"""SPEC-006B-3: conservative, opt-in runtime queue provenance on Alembic 006B-2.

Only an explicitly migrated SQLite database enables these writes. Existing
unversioned local databases keep their original behavior. Missing historical
segments never inherit the session's current queue by inference.
"""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Engine, func, insert, select, text, update
from sqlalchemy.orm import Session

from handoff_hub.poc_db import HandoffSession, Message, SessionEvent, SessionTransfer, utc_now
from handoff_hub.provenance_schema import (
    MESSAGE_QUEUE_PROVENANCE,
    SESSION_EVENT_QUEUE_PROVENANCE,
    SESSION_QUEUE_SEGMENTS,
)

REQUIRED_REVISION = "006b2_queue_provenance"


class ProvenanceRecorder:
    """Writes only verified boundaries and marks ambiguous records fail-closed."""

    def __init__(self, engine: Engine) -> None:
        self.enabled = False
        if engine.dialect.name != "sqlite":
            return
        with engine.connect() as connection:
            known = connection.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='alembic_version'"
            )).first()
            if known is None:
                return  # Unversioned POC: NEVER create provenance tables implicitly.
            revision = connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one()
            if revision == "006b1_poc_baseline":
                return
            if revision != REQUIRED_REVISION:
                raise RuntimeError(f"Unknown database revision: {revision}")
            actual = set(connection.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).scalars())
            expected = {
                "session_queue_segments",
                "message_queue_provenance",
                "session_event_queue_provenance",
            }
            if not expected.issubset(actual):
                raise RuntimeError("Queue provenance schema is missing required tables")
        self.enabled = True

    def _current(self, db: Session, session_id: str):
        rows = db.execute(
            select(SESSION_QUEUE_SEGMENTS)
            .where(
                SESSION_QUEUE_SEGMENTS.c.session_id == session_id,
                SESSION_QUEUE_SEGMENTS.c.ended_at.is_(None),
            )
            .order_by(SESSION_QUEUE_SEGMENTS.c.ordinal.desc())
        ).mappings().all()
        if len(rows) > 1:
            raise RuntimeError("Overlapping queue provenance segments; aborting write")
        return rows[0] if rows else None

    def intake(self, db: Session, handoff: HandoffSession) -> str | None:
        """Record a VERIFIED first queue, only at the moment of new intake."""
        if not self.enabled:
            return None
        if self._current(db, handoff.id) is not None:
            raise RuntimeError("Cannot create a duplicate intake segment")
        segment_id = str(uuid4())
        db.execute(insert(SESSION_QUEUE_SEGMENTS).values(
            id=segment_id,
            session_id=handoff.id,
            queue_id=handoff.queue_id,
            ordinal=0,
            started_at=handoff.created_at or utc_now(),
            ended_at=None,
            transfer_id=None,
            provenance_state="VERIFIED",
        ))
        return segment_id

    def transfer(self, db: Session, handoff: HandoffSession,
                 transfer: SessionTransfer) -> str | None:
        """Close the known source and open a verified destination at transfer time.

        For legacy sessions without provenance, no source history is invented.
        The newly observed destination is verified, while earlier content stays
        unassigned and inaccessible to queue-scoped history readers.
        """
        if not self.enabled:
            return None
        current = self._current(db, handoff.id)
        if current and current["queue_id"] != transfer.from_queue_id:
            raise RuntimeError("Stored provenance conflicts with the source queue")
        if current:
            db.execute(
                update(SESSION_QUEUE_SEGMENTS)
                .where(SESSION_QUEUE_SEGMENTS.c.id == current["id"])
                .values(ended_at=transfer.created_at or utc_now())
            )
        maximum = db.scalar(
            select(func.max(SESSION_QUEUE_SEGMENTS.c.ordinal)).where(
                SESSION_QUEUE_SEGMENTS.c.session_id == handoff.id
            )
        )
        db.execute(insert(SESSION_QUEUE_SEGMENTS).values(
            id=str(uuid4()),
            session_id=handoff.id,
            queue_id=transfer.to_queue_id,
            ordinal=(maximum + 1 if maximum is not None else 0),
            started_at=transfer.created_at or utc_now(),
            ended_at=None,
            transfer_id=transfer.id,
            provenance_state="VERIFIED",
        ))
        return current["id"] if current else None

    def message(self, db: Session, handoff: HandoffSession, message: Message) -> None:
        """Associate new messages only with an unequivocally active queue segment."""
        if not self.enabled:
            return
        current = self._current(db, handoff.id)
        segment_id = current["id"] if current and current["queue_id"] == handoff.queue_id else None
        db.execute(insert(MESSAGE_QUEUE_PROVENANCE).values(
            message_id=message.id,
            segment_id=segment_id,
            assigned_by="RUNTIME",
            confidence="VERIFIED" if segment_id else "UNDETERMINED",
        ))

    def event_for_handoff(self, db: Session, handoff: HandoffSession,
                          event: SessionEvent) -> None:
        """Attribute a NEW operational event only to a matching open segment.

        Legacy/unproven sessions receive UNDETERMINED, never current-queue
        inference. This executes inside the caller's existing transaction.
        """
        if not self.enabled:
            return
        db.flush()
        current = self._current(db, handoff.id)
        segment_id = (
            current["id"]
            if current and current["queue_id"] == handoff.queue_id
            and current["provenance_state"] == "VERIFIED"
            else None
        )
        self.event(db, event, segment_id)

    def event(self, db: Session, event: SessionEvent,
              verified_segment_id: str | None) -> None:
        """Do not guess which queue owns unclassified historical or transition events."""
        if not self.enabled:
            return
        db.execute(insert(SESSION_EVENT_QUEUE_PROVENANCE).values(
            event_id=event.id,
            segment_id=verified_segment_id,
            assigned_by="RUNTIME",
            confidence="VERIFIED" if verified_segment_id else "UNDETERMINED",
        ))

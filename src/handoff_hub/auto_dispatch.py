"""Automatic transactional FIFO + fair, persisted queue round-robin for local POC.

One SQLite writer at a time via BEGIN IMMEDIATE. Do not port locking to SQL Server.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from handoff_hub.poc_auth import HEARTBEAT_MAX_AGE, naive_utc
from handoff_hub.poc_db import (
    AuthSession,
    AuthUser,
    DispatchTurn,
    HandoffOffer,
    HandoffSession,
    Operator,
    Queue,
    QueueMembership,
    SessionEvent,
    utc_now,
)
from handoff_hub.provenance_writer import ProvenanceRecorder
from handoff_hub.queue_lifecycle import queue_active

OFFER_SECONDS = 120
DECLINE_COOLDOWN_SECONDS = 120


def run_dispatch_cycle(factory, provenance: ProvenanceRecorder | None = None) -> dict:
    """Atomic offer reservations; run periodically in one local backend instance."""
    if provenance is None:
        provenance = ProvenanceRecorder(factory.kw["bind"])
    result = {"offered": 0, "expired": 0}
    with factory() as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        now = naive_utc()
        online_cutoff = now - timedelta(seconds=HEARTBEAT_MAX_AGE)
        live_ids = set(db.scalars(
            select(AuthUser.operator_id)
            .join(AuthSession, AuthSession.user_id == AuthUser.id)
            .where(
                AuthUser.role == "OPERATOR",
                AuthUser.is_active.is_(True),
                AuthSession.revoked.is_(False),
                AuthSession.expires_at > now,
                AuthSession.last_seen > online_cutoff,
            )
        ).all())

        # Cancel unaccepted reservations if the operator is disconnected or timed out.
        pending = db.scalars(select(HandoffOffer).where(
            HandoffOffer.status == "PENDING"
        )).all()
        for offer in pending:
            h = db.get(HandoffSession, offer.session_id)
            op = db.get(Operator, offer.operator_id)
            if (offer.expires_at > now and offer.operator_id in live_ids and
                    op is not None and op.presence == "AVAILABLE"):
                continue
            offer.status = "EXPIRED"
            offer.resolved_at = utc_now()
            if h and h.status == "OFFERED" and h.operator_id == offer.operator_id:
                h.operator_id = None
                h.status = "QUEUED"
                h.updated_at = utc_now()
                event = SessionEvent(
                    session_id=h.id, event_type="OFFER_EXPIRED", actor="auto-dispatch"
                )
                db.add(event)
                provenance.event_for_handoff(db, h, event)
                result["expired"] += 1
        db.flush()

        for queue in db.scalars(select(Queue).order_by(Queue.id)).all():
            if not queue_active(db, queue.id, enabled=provenance.queue_lifecycle_enabled):
                continue
            waiting = db.scalars(
                select(HandoffSession)
                .where(HandoffSession.queue_id == queue.id,
                       HandoffSession.status == "QUEUED")
                .order_by(HandoffSession.created_at, HandoffSession.id)
            ).all()
            members = set(db.scalars(
                select(QueueMembership.operator_id)
                .where(QueueMembership.queue_id == queue.id)
            ).all())
            ops = db.scalars(
                select(Operator)
                .where(Operator.id.in_(members), Operator.id.in_(live_ids),
                       Operator.operation_id == queue.operation_id,
                       Operator.presence == "AVAILABLE")
                .order_by(Operator.id)
            ).all()
            if not ops or not waiting:
                continue
            turns = {
                turn.operator_id: turn
                for turn in db.scalars(
                    select(DispatchTurn).where(DispatchTurn.queue_id == queue.id)
                ).all()
            }
            # Queue fairness: move recipient to back at OFFER, not at acceptance.
            for handoff in waiting:
                occupied = dict(db.execute(
                    select(HandoffSession.operator_id, func.count())
                    .where(HandoffSession.status.in_(("ACTIVE", "OFFERED")))
                    .group_by(HandoffSession.operator_id)
                ).all())
                eligible = []
                for op in ops:
                    if occupied.get(op.id, 0) >= op.capacity:
                        continue
                    was_declined = db.scalar(select(HandoffOffer.id).where(
                        HandoffOffer.session_id == handoff.id,
                        HandoffOffer.operator_id == op.id,
                        HandoffOffer.status.in_(("DECLINED", "EXPIRED")),
                        HandoffOffer.resolved_at > now - timedelta(
                            seconds=DECLINE_COOLDOWN_SECONDS
                        ),
                    ).limit(1))
                    if was_declined:
                        continue
                    turn = turns.get(op.id)
                    eligible.append((turn.last_offered_at if turn else None, op.id, op))
                if not eligible:
                    continue
                # Never-offered operators first; otherwise oldest last_offer wins.
                eligible.sort(key=lambda row: (row[0] is not None, row[0] or now, row[1]))
                op = eligible[0][2]
                handoff.status = "OFFERED"
                handoff.operator_id = op.id
                handoff.updated_at = utc_now()
                db.add(HandoffOffer(
                    session_id=handoff.id, operator_id=op.id, status="PENDING",
                    expires_at=utc_now() + timedelta(seconds=OFFER_SECONDS),
                ))
                event = SessionEvent(
                    session_id=handoff.id, event_type="OFFERED_AUTO", actor=op.id
                )
                db.add(event)
                provenance.event_for_handoff(db, handoff, event)
                turn = turns.get(op.id)
                if turn is None:
                    turn = DispatchTurn(
                        queue_id=queue.id, operator_id=op.id, total_offers=0
                    )
                    db.add(turn)
                    turns[op.id] = turn
                # Normalize SQLite timestamps: do not sort aware and naive datetimes.
                turn.last_offered_at = naive_utc()
                turn.total_offers += 1
                db.flush()
                result["offered"] += 1
        db.commit()
    return result

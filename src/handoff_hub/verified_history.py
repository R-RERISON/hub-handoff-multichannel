"""SPEC-006B-4: queue-scoped read of runtime-verified history only.

This deliberately separate endpoint does not relax the legacy full-history
authorization on /messages or /timeline. No historical inference or backfill.
"""
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select

from handoff_hub.poc_db import HandoffSession, Message, SessionEvent
from handoff_hub.provenance_schema import (
    MESSAGE_QUEUE_PROVENANCE,
    SESSION_EVENT_QUEUE_PROVENANCE,
    SESSION_QUEUE_SEGMENTS,
)
from handoff_hub.provenance_writer import ProvenanceRecorder
from handoff_hub.queue_authorization import SCOPED_ROLES, require_queue


def register_verified_history(
    factory, authenticate: Callable, provenance: ProvenanceRecorder,
) -> APIRouter:
    router = APIRouter(prefix="/v1", dependencies=[Depends(authenticate)])

    @router.get("/history/verified-sessions")
    def verified_sessions(
        request: Request,
        queue_id: str = Query(min_length=1, max_length=60),
        page: int = Query(default=1, ge=1, le=1000),
        page_size: int = Query(default=25, ge=1, le=50),
    ):
        """Discover tickets by VERIFIED evidence in one explicitly granted queue.

        No requester, subject, current queue, cross-queue transfer chain or
        global status is disclosed. Paginate after applying authorization.
        """
        principal = request.state.principal
        if principal.role not in SCOPED_ROLES:
            raise HTTPException(403, "Consulta reservada à supervisão e auditoria")
        with factory() as db:
            require_queue(db, principal, queue_id)
            if not provenance.enabled:
                return {
                    "scope": "RUNTIME_VERIFIED_QUEUE_ONLY",
                    "queue_id": queue_id,
                    "schema_ready": False,
                    "partial_history": True,
                    "tickets": [],
                    "page": page,
                    "next_page": None,
                }

            seg = SESSION_QUEUE_SEGMENTS
            messages_with_proof = (
                select(MESSAGE_QUEUE_PROVENANCE.c.message_id)
                .join(Message, Message.id == MESSAGE_QUEUE_PROVENANCE.c.message_id)
                .where(
                    MESSAGE_QUEUE_PROVENANCE.c.segment_id == seg.c.id,
                    MESSAGE_QUEUE_PROVENANCE.c.confidence == "VERIFIED",
                    MESSAGE_QUEUE_PROVENANCE.c.assigned_by == "RUNTIME",
                    Message.session_id == HandoffSession.id,
                ).exists()
            )
            events_with_proof = (
                select(SESSION_EVENT_QUEUE_PROVENANCE.c.event_id)
                .join(
                    SessionEvent,
                    SessionEvent.id == SESSION_EVENT_QUEUE_PROVENANCE.c.event_id,
                )
                .where(
                    SESSION_EVENT_QUEUE_PROVENANCE.c.segment_id == seg.c.id,
                    SESSION_EVENT_QUEUE_PROVENANCE.c.confidence == "VERIFIED",
                    SESSION_EVENT_QUEUE_PROVENANCE.c.assigned_by == "RUNTIME",
                    SessionEvent.session_id == HandoffSession.id,
                ).exists()
            )
            last_segment_start = func.max(seg.c.started_at).label("last_segment_start")
            stmt = (
                select(HandoffSession.id, last_segment_start)
                .join(seg, seg.c.session_id == HandoffSession.id)
                .where(
                    HandoffSession.operation_id == principal.operation_id,
                    seg.c.queue_id == queue_id,
                    seg.c.provenance_state == "VERIFIED",
                    or_(messages_with_proof, events_with_proof),
                )
                .group_by(HandoffSession.id)
                .order_by(last_segment_start.desc(), HandoffSession.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size + 1)
            )
            rows = db.execute(stmt).all()
            visible = rows[:page_size]
            return {
                "scope": "RUNTIME_VERIFIED_QUEUE_ONLY",
                "queue_id": queue_id,
                "schema_ready": True,
                "partial_history": True,
                "tickets": [
                    {"session_id": session_id, "segment_started_at": started_at.isoformat()}
                    for session_id, started_at in visible
                ],
                "page": page,
                "next_page": page + 1 if len(rows) > page_size else None,
            }

    @router.get("/handoffs/{handoff_id}/verified-history")
    def verified_history(
        handoff_id: str,
        request: Request,
        queue_id: str = Query(min_length=1, max_length=60),
        message_page: int = Query(default=1, ge=1, le=1000),
        event_page: int = Query(default=1, ge=1, le=1000),
        page_size: int = Query(default=25, ge=1, le=50),
    ):
        principal = request.state.principal
        # An operator's operational context is governed by ownership; neither
        # the operator nor the admin needs this additional scoped read surface.
        if principal.role not in SCOPED_ROLES:
            raise HTTPException(403, "Consulta reservada à supervisão e auditoria")

        with factory() as db:
            # Keep authorization and data retrieval within the same DB read
            # transaction. Revoked grants take effect on the next request.
            require_queue(db, principal, queue_id)
            handoff = db.get(HandoffSession, handoff_id)
            if handoff is None or handoff.operation_id != principal.operation_id:
                raise HTTPException(404, "Histórico não encontrado")
            if not provenance.enabled:
                # The original 17-table POC cannot prove queue ownership.
                raise HTTPException(404, "Histórico verificado indisponível")

            segments = select(SESSION_QUEUE_SEGMENTS.c.id).where(
                SESSION_QUEUE_SEGMENTS.c.session_id == handoff_id,
                SESSION_QUEUE_SEGMENTS.c.queue_id == queue_id,
                SESSION_QUEUE_SEGMENTS.c.provenance_state == "VERIFIED",
            )
            # No current-queue fallback. A queue grant is not evidence that a
            # legacy message or event belonged to that queue.
            if db.execute(segments.limit(1)).first() is None:
                raise HTTPException(404, "Histórico não encontrado")

            message_rows = db.execute(
                select(Message.id, Message.sender, Message.content, Message.created_at)
                .join(
                    MESSAGE_QUEUE_PROVENANCE,
                    MESSAGE_QUEUE_PROVENANCE.c.message_id == Message.id,
                )
                .join(
                    SESSION_QUEUE_SEGMENTS,
                    SESSION_QUEUE_SEGMENTS.c.id == MESSAGE_QUEUE_PROVENANCE.c.segment_id,
                )
                .where(
                    Message.session_id == handoff_id,
                    SESSION_QUEUE_SEGMENTS.c.session_id == handoff_id,
                    SESSION_QUEUE_SEGMENTS.c.queue_id == queue_id,
                    SESSION_QUEUE_SEGMENTS.c.provenance_state == "VERIFIED",
                    MESSAGE_QUEUE_PROVENANCE.c.confidence == "VERIFIED",
                    MESSAGE_QUEUE_PROVENANCE.c.assigned_by == "RUNTIME",
                )
                .order_by(Message.created_at, Message.id)
                .offset((message_page - 1) * page_size)
                .limit(page_size + 1)
            ).all()
            event_rows = db.execute(
                select(SessionEvent.id, SessionEvent.event_type, SessionEvent.actor,
                       SessionEvent.created_at)
                .join(
                    SESSION_EVENT_QUEUE_PROVENANCE,
                    SESSION_EVENT_QUEUE_PROVENANCE.c.event_id == SessionEvent.id,
                )
                .join(
                    SESSION_QUEUE_SEGMENTS,
                    SESSION_QUEUE_SEGMENTS.c.id == SESSION_EVENT_QUEUE_PROVENANCE.c.segment_id,
                )
                .where(
                    SessionEvent.session_id == handoff_id,
                    SESSION_QUEUE_SEGMENTS.c.session_id == handoff_id,
                    SESSION_QUEUE_SEGMENTS.c.queue_id == queue_id,
                    SESSION_QUEUE_SEGMENTS.c.provenance_state == "VERIFIED",
                    SESSION_EVENT_QUEUE_PROVENANCE.c.confidence == "VERIFIED",
                    SESSION_EVENT_QUEUE_PROVENANCE.c.assigned_by == "RUNTIME",
                )
                .order_by(SessionEvent.created_at, SessionEvent.id)
                .offset((event_page - 1) * page_size)
                .limit(page_size + 1)
            ).all()

            # No transfer reason, current queue, requester, other queue IDs,
            # total counts or summary fields: those can expose another scope.
            return {
                "scope": "RUNTIME_VERIFIED_QUEUE_ONLY",
                "queue_id": queue_id,
                "partial_history": True,
                "page_size": page_size,
                "message_page": message_page,
                "event_page": event_page,
                "message_next_page": (
                    message_page + 1 if len(message_rows) > page_size else None
                ),
                "event_next_page": (
                    event_page + 1 if len(event_rows) > page_size else None
                ),
                "messages": [
                    {"id": mid, "sender": sender, "content": body,
                     "created_at": at.isoformat()}
                    for mid, sender, body, at in message_rows[:page_size]
                ],
                "events": [
                    {"type": kind, "actor": actor, "at": at.isoformat()}
                    for _, kind, actor, at in event_rows[:page_size]
                ],
            }

    return router

"""SPEC-006B-4.1: queue-scoped read of runtime-verified history only.

This deliberately separate endpoint does not relax the legacy full-history
authorization on /messages or /timeline. No historical inference or backfill.
"""
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

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

    @router.get("/handoffs/{handoff_id}/verified-history")
    def verified_history(
        handoff_id: str,
        request: Request,
        queue_id: str = Query(min_length=1, max_length=60),
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
            ).all()

            # No transfer reason, current queue, requester, other queue IDs,
            # total counts or summary fields: those can expose another scope.
            return {
                "scope": "RUNTIME_VERIFIED_QUEUE_ONLY",
                "queue_id": queue_id,
                "partial_history": True,
                "messages": [
                    {"id": mid, "sender": sender, "content": body,
                     "created_at": at.isoformat()}
                    for mid, sender, body, at in message_rows
                ],
                "events": [
                    {"type": kind, "actor": actor, "at": at.isoformat()}
                    for _, kind, actor, at in event_rows
                ],
            }

    return router

"""SQLite POC: offer/accept/decline/transfer workflow, isolated from Teams.

This router intentionally retains the local shared POC key. operator_id is a
simulated identity, NOT authenticated impersonation; do not expose publicly.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from handoff_hub.domain.state_machine import HandoffStatus, assert_transition
from handoff_hub.poc_db import (
    HandoffOffer,
    HandoffSession,
    Operator,
    Queue,
    QueueMembership,
    SessionEvent,
    SessionTransfer,
    utc_now,
)
from handoff_hub.provenance_writer import ProvenanceRecorder
from handoff_hub.queue_lifecycle import queue_active, require_active

OFFER_SECONDS = 120
DECLINE_COOLDOWN_SECONDS = 120
RESERVED_STATUSES = ("OFFERED", "ACTIVE")


class OfferRequest(BaseModel):
    operation_id: str = "demo"
    queue_id: str = "n1"


class OperatorAction(BaseModel):
    operator_id: str = Field(min_length=1, max_length=60)


class TransferRequest(OperatorAction):
    queue_id: str = Field(min_length=1, max_length=60)
    reason: str = Field(min_length=3, max_length=300)


def as_offer(offer: HandoffOffer, session: HandoffSession) -> dict:
    expiry = offer.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    return {
        "offer_id": offer.id,
        "session_id": session.id,
        "operator_id": offer.operator_id,
        "queue_id": session.queue_id,
        "requester_label": session.requester_label,
        "subject": session.subject,
        "status": offer.status,
        "expires_at": expiry.isoformat(),
    }


def utc_naive() -> datetime:
    """SQLite loads DateTime(timezone=True) without tzinfo; all values are UTC."""
    return datetime.now(UTC).replace(tzinfo=None)


def register_operator_workflow(
    factory,
    authenticate: Callable,
    exclusive_tx: Callable,
    as_handoff: Callable,
    provenance: ProvenanceRecorder,
) -> APIRouter:
    router = APIRouter(prefix="/v1", dependencies=[Depends(authenticate)])

    def event(db: Session, handoff: HandoffSession, name: str, actor: str) -> None:
        row = SessionEvent(session_id=handoff.id, event_type=name, actor=actor)
        db.add(row)
        provenance.event_for_handoff(db, handoff, row)

    def requeue_expired(db: Session) -> int:
        now = utc_naive()
        expired = db.scalars(
            select(HandoffOffer).where(
                HandoffOffer.status == "PENDING", HandoffOffer.expires_at <= now
            )
        ).all()
        changed = 0
        for offer in expired:
            offer.status = "EXPIRED"
            offer.resolved_at = utc_now()
            session = db.get(HandoffSession, offer.session_id)
            if (session is not None and session.status == "OFFERED"
                    and session.operator_id == offer.operator_id):
                assert_transition(HandoffStatus.OFFERED, HandoffStatus.QUEUED)
                session.status = "QUEUED"
                session.operator_id = None
                session.updated_at = utc_now()
                event(db, session, "OFFER_EXPIRED", offer.operator_id)
                changed += 1
        return changed

    def get_pending_offer(db: Session, handoff_id: str, operator_id: str):
        handoff = db.get(HandoffSession, handoff_id)
        if handoff is None:
            raise HTTPException(404, "Atendimento inexistente")
        offer = db.scalar(
            select(HandoffOffer)
            .where(
                HandoffOffer.session_id == handoff_id,
                HandoffOffer.operator_id == operator_id,
                HandoffOffer.status == "PENDING",
            )
            .order_by(HandoffOffer.created_at.desc())
            .limit(1)
        )
        if offer is None or handoff.status != "OFFERED" or handoff.operator_id != operator_id:
            raise HTTPException(409, "Oferta inexistente ou já resolvida para este operador")
        return handoff, offer

    @router.post("/dispatch/offer")
    def offer_next(body: OfferRequest):
        """Reserve capacity for up to two minutes, without marking the chat ACTIVE."""
        with factory() as db:
            exclusive_tx(db)
            if requeue_expired(db):
                # This POC uses autoflush=False; release reservations before SELECTs.
                db.flush()
            queue = db.get(Queue, body.queue_id)
            if queue is None or queue.operation_id != body.operation_id:
                raise HTTPException(404, "Fila não encontrada")
            require_active(db, queue.id, enabled=provenance.queue_lifecycle_enabled)
            waiting = db.scalar(
                select(HandoffSession)
                .where(
                    HandoffSession.queue_id == body.queue_id,
                    HandoffSession.operation_id == body.operation_id,
                    HandoffSession.status == "QUEUED",
                )
                .order_by(HandoffSession.created_at, HandoffSession.id)
                .limit(1)
            )
            if waiting is None:
                db.commit()
                return {"result": "empty_queue"}
            ids = db.scalars(
                select(QueueMembership.operator_id)
                .where(QueueMembership.queue_id == body.queue_id)
            ).all()
            declined_ids = set(db.scalars(
                select(HandoffOffer.operator_id)
                .where(
                    HandoffOffer.session_id == waiting.id,
                    HandoffOffer.status == "DECLINED",
                    HandoffOffer.resolved_at > (
                        utc_naive() - timedelta(seconds=DECLINE_COOLDOWN_SECONDS)
                    ),
                )
            ).all())
            operators = db.scalars(
                select(Operator)
                .where(
                    Operator.id.in_(ids),
                    Operator.id.not_in(declined_ids),
                    Operator.operation_id == body.operation_id,
                    Operator.presence == "AVAILABLE",
                )
                .order_by(Operator.id)
            ).all()
            available: list[tuple[int, Operator]] = []
            for op in operators:
                occupied = db.scalar(
                    select(func.count()).select_from(HandoffSession).where(
                        HandoffSession.operator_id == op.id,
                        HandoffSession.status.in_(RESERVED_STATUSES),
                    )
                ) or 0
                if occupied < op.capacity:
                    available.append((occupied, op))
            if not available:
                db.commit()
                return {"result": "no_operator_available"}
            _, op = min(available, key=lambda pair: (pair[0], pair[1].id))
            assert_transition(HandoffStatus.QUEUED, HandoffStatus.OFFERED)
            waiting.operator_id = op.id
            waiting.status = "OFFERED"
            waiting.updated_at = utc_now()
            offer = HandoffOffer(
                session_id=waiting.id,
                operator_id=op.id,
                status="PENDING",
                expires_at=utc_now() + timedelta(seconds=OFFER_SECONDS),
            )
            db.add(offer)
            event(db, waiting, "OFFERED", op.id)
            db.flush()
            result = as_offer(offer, waiting)
            db.commit()
            return {"result": "offered", "offer": result}

    @router.get("/operators/{operator_id}/work")
    def operator_work(operator_id: str):
        with factory() as db:
            op = db.get(Operator, operator_id)
            if op is None:
                raise HTTPException(404, "Operador não encontrado")
            offers = db.scalars(
                select(HandoffOffer)
                .where(HandoffOffer.operator_id == operator_id, HandoffOffer.status == "PENDING")
                .order_by(HandoffOffer.created_at)
            ).all()
            now = utc_naive()
            offered = [
                as_offer(offer, handoff)
                for offer in offers
                if offer.expires_at > now
                if (handoff := db.get(HandoffSession, offer.session_id)) is not None
                and handoff.status == "OFFERED"
                and handoff.operator_id == operator_id
            ]
            active = db.scalars(
                select(HandoffSession)
                .where(
                    HandoffSession.operator_id == operator_id,
                    HandoffSession.status == "ACTIVE",
                )
                .order_by(HandoffSession.created_at)
            ).all()
            return {
                "operator": {"id": op.id, "name": op.name,
                             "presence": op.presence, "capacity": op.capacity},
                "offers": offered,
                "active": [as_handoff(h) for h in active],
            }

    @router.post("/handoffs/{handoff_id}/accept")
    def accept_offer(handoff_id: str, body: OperatorAction):
        with factory() as db:
            exclusive_tx(db)
            handoff, offer = get_pending_offer(db, handoff_id, body.operator_id)
            if offer.expires_at <= utc_naive():
                requeue_expired(db)
                db.commit()
                raise HTTPException(409, "Oferta expirada e devolvida à fila")
            op = db.get(Operator, body.operator_id)
            if op is None or op.operation_id != handoff.operation_id or op.presence != "AVAILABLE":
                raise HTTPException(409, "Operador indisponível para aceitar")
            if db.get(QueueMembership, (handoff.queue_id, op.id)) is None:
                raise HTTPException(403, "Operador não pertence à fila")
            assert_transition(HandoffStatus.OFFERED, HandoffStatus.ACTIVE)
            offer.status = "ACCEPTED"
            offer.resolved_at = utc_now()
            handoff.status = "ACTIVE"
            handoff.updated_at = utc_now()
            event(db, handoff, "ACCEPTED", op.id)
            db.commit()
            return as_handoff(handoff)

    @router.post("/handoffs/{handoff_id}/decline")
    def decline_offer(handoff_id: str, body: OperatorAction):
        with factory() as db:
            exclusive_tx(db)
            handoff, offer = get_pending_offer(db, handoff_id, body.operator_id)
            if offer.expires_at <= utc_naive():
                requeue_expired(db)
                db.commit()
                raise HTTPException(409, "Oferta expirada e devolvida à fila")
            assert_transition(HandoffStatus.OFFERED, HandoffStatus.QUEUED)
            offer.status = "DECLINED"
            offer.resolved_at = utc_now()
            handoff.status = "QUEUED"
            handoff.operator_id = None
            handoff.updated_at = utc_now()
            event(db, handoff, "DECLINED", body.operator_id)
            db.commit()
            return as_handoff(handoff)

    @router.get("/handoffs/{handoff_id}/transfer-targets")
    def transfer_targets(handoff_id: str):
        """Offer transfer destinations, independent of dispatch membership.

        Authentication/ownership is enforced by the shared router dependency;
        this endpoint additionally requires an ACTIVE session before disclosing
        destinations. The POC has no queue lifecycle/routing policy yet, so all
        other queues from the same operation are valid destinations.
        """
        with factory() as db:
            handoff = db.get(HandoffSession, handoff_id)
            if handoff is None:
                raise HTTPException(404, "Atendimento inexistente")
            if handoff.status != "ACTIVE" or handoff.operator_id is None:
                raise HTTPException(409, "Transferência exige atendimento ativo")
            destinations = db.scalars(
                select(Queue)
                .where(
                    Queue.operation_id == handoff.operation_id,
                    Queue.id != handoff.queue_id,
                )
                .order_by(Queue.name, Queue.id)
            ).all()
            return {
                "session_id": handoff.id,
                "source_queue_id": handoff.queue_id,
                "destinations": [
                    {"id": q.id, "name": q.name} for q in destinations
                    if queue_active(db, q.id, enabled=provenance.queue_lifecycle_enabled)
                ],
            }

    @router.post("/handoffs/{handoff_id}/transfer")
    def transfer_handoff(handoff_id: str, body: TransferRequest):
        """Transfer to queue, release current capacity and preserve original owner."""
        with factory() as db:
            exclusive_tx(db)
            handoff = db.get(HandoffSession, handoff_id)
            if handoff is None:
                raise HTTPException(404, "Atendimento inexistente")
            if handoff.status != "ACTIVE" or handoff.operator_id != body.operator_id:
                raise HTTPException(409, "Apenas o operador responsável pode transferir sessão ativa")
            queue = db.get(Queue, body.queue_id)
            if queue is None or queue.operation_id != handoff.operation_id:
                raise HTTPException(422, "Fila destino inexistente ou de outra operação")
            if queue.id == handoff.queue_id:
                raise HTTPException(422, "Escolha uma fila de destino diferente da atual")
            require_active(db, queue.id, enabled=provenance.queue_lifecycle_enabled)
            assert_transition(HandoffStatus.ACTIVE, HandoffStatus.TRANSFER_PENDING)
            assert_transition(HandoffStatus.TRANSFER_PENDING, HandoffStatus.QUEUED)
            transfer = SessionTransfer(
                session_id=handoff.id,
                from_queue_id=handoff.queue_id,
                to_queue_id=queue.id,
                from_operator_id=body.operator_id,
                reason=body.reason,
            )
            db.add(transfer)
            db.flush()
            source_segment_id = provenance.transfer(db, handoff, transfer)
            transfer_event = SessionEvent(
                session_id=handoff.id,
                event_type="TRANSFERRED",
                actor=body.operator_id,
            )
            db.add(transfer_event)
            db.flush()
            provenance.event(db, transfer_event, source_segment_id)
            handoff.queue_id = queue.id
            handoff.operator_id = None
            handoff.status = "QUEUED"
            handoff.updated_at = utc_now()
            db.commit()
            return as_handoff(handoff)

    @router.post("/operators/{operator_id}/handoffs/{handoff_id}/close")
    def close_operator_handoff(operator_id: str, handoff_id: str):
        """POC identity checked against assignment, but not authenticated per operator."""
        with factory() as db:
            exclusive_tx(db)
            handoff = db.get(HandoffSession, handoff_id)
            if handoff is None:
                raise HTTPException(404, "Atendimento inexistente")
            if handoff.operator_id != operator_id:
                raise HTTPException(403, "Operador não é responsável pelo atendimento")
            if handoff.status != "ACTIVE":
                raise HTTPException(409, "Somente atendimento ativo pode ser encerrado")
            handoff.status = "CLOSED"
            handoff.updated_at = utc_now()
            event(db, handoff, "CLOSED", operator_id)
            db.commit()
            return as_handoff(handoff)

    @router.post("/offers/expire")
    def expire_offers():
        """Explicit demo reaper; eventual worker replaces this in production."""
        with factory() as db:
            exclusive_tx(db)
            expired = requeue_expired(db)
            db.commit()
            return {"expired": expired}

    @router.get("/handoffs/{handoff_id}/timeline")
    def timeline(handoff_id: str):
        with factory() as db:
            if db.get(HandoffSession, handoff_id) is None:
                raise HTTPException(404, "Atendimento inexistente")
            events = db.scalars(
                select(SessionEvent).where(SessionEvent.session_id == handoff_id)
                .order_by(SessionEvent.created_at, SessionEvent.id)
            ).all()
            transfers = db.scalars(
                select(SessionTransfer).where(SessionTransfer.session_id == handoff_id)
                .order_by(SessionTransfer.created_at, SessionTransfer.id)
            ).all()
            return {
                "events": [
                    {"type": e.event_type, "actor": e.actor, "at": e.created_at.isoformat()}
                    for e in events
                ],
                "transfers": [
                    {"from_queue_id": t.from_queue_id, "to_queue_id": t.to_queue_id,
                     "operator_id": t.from_operator_id, "reason": t.reason,
                     "from_operator_name": (
                         op.name if (op := db.get(Operator, t.from_operator_id))
                         else t.from_operator_id
                     ),
                     "from_queue_name": (
                         source.name if (source := db.get(Queue, t.from_queue_id))
                         else t.from_queue_id
                     ),
                     "to_queue_name": (
                         target.name if (target := db.get(Queue, t.to_queue_id))
                         else t.to_queue_id
                     ),
                     "at": t.created_at.isoformat()}
                    for t in transfers
                ],
            }

    return router

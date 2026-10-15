"""Local-only demonstration API. No Teams delivery, real users or production authentication."""
from __future__ import annotations

import hmac
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from handoff_hub.operator_workflow import register_operator_workflow
from handoff_hub.poc_db import (
    HandoffSession,
    Integration,
    Message,
    Operation,
    Operator,
    OutboxEvent,
    Queue,
    QueueMembership,
    SessionEvent,
    make_session_factory,
    utc_now,
)


class HandoffCreate(BaseModel):
    operation_id: str = "demo"
    integration_id: str = "demo-bot"
    queue_id: str = "n1"
    external_conversation_id: str = Field(min_length=1, max_length=200)
    requester_label: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=200)


class MessageCreate(BaseModel):
    sender: Literal["USER", "OPERATOR"]
    content: str = Field(min_length=1, max_length=4000)
    external_message_id: str = Field(min_length=1, max_length=128)
    operator_id: str | None = Field(default=None, max_length=60)


class DispatchRequest(BaseModel):
    queue_id: str = "n1"
    operation_id: str = "demo"


class PresenceUpdate(BaseModel):
    presence: Literal["AVAILABLE", "AWAY", "OFFLINE"]


def as_handoff(h: HandoffSession) -> dict:
    return {"id": h.id, "operation_id": h.operation_id, "integration_id": h.integration_id,
            "queue_id": h.queue_id, "requester_label": h.requester_label,
            "external_conversation_id": h.external_conversation_id, "subject": h.subject,
            "status": h.status, "operator_id": h.operator_id,
            "created_at": h.created_at.isoformat(), "updated_at": h.updated_at.isoformat()}


def create_app(database_url: str | None = None, api_key: str | None = None) -> FastAPI:
    """Bind to 127.0.0.1: security is a local POC key, not operator/tenant RBAC."""
    database_url = database_url or os.getenv("HANDOFF_DB_URL", "sqlite:///./data/handoff-poc.db")
    api_key = api_key if api_key is not None else os.getenv("HANDOFF_POC_KEY", "")
    if database_url.startswith("sqlite:///./"):
        Path(database_url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)
    factory, engine = make_session_factory(database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="Handoff Hub — SQLite POC", version="0.3.0-poc", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
                       allow_credentials=False, allow_methods=["GET", "POST", "PATCH"],
                       allow_headers=["X-POC-Key", "Idempotency-Key", "Content-Type"])

    def authenticate(x_poc_key: str | None = Header(default=None)) -> None:
        if not api_key or not x_poc_key or not hmac.compare_digest(api_key, x_poc_key):
            raise HTTPException(401, "Chave local de demonstração inválida")

    def exclusive_tx(db):
        """SQLite writer lock. Do not reuse this locking syntax in SQL Server."""
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")

    @app.get("/health/live")
    def live():
        return {"status": "alive", "version": "0.3.0-poc"}

    @app.get("/health/ready")
    def ready(response: Response):
        if not api_key:
            response.status_code = 503
            return {"status": "not_ready", "reason": "HANDOFF_POC_KEY_not_set"}
        return {"status": "poc_ready", "scope": "local_only"}

    @app.post("/v1/demo/bootstrap", dependencies=[Depends(authenticate)])
    def bootstrap():
        """Seed only synthetic identities, never operational records."""
        with factory.begin() as db:
            if db.get(Operation, "demo") is None:
                db.add(Operation(id="demo", name="Operação Demonstrativa"))
                db.flush()
            if db.get(Integration, "demo-bot") is None:
                db.add(Integration(id="demo-bot", operation_id="demo", name="Bot Simulado", channel="simulator"))
            if db.get(Queue, "n1") is None:
                db.add(Queue(id="n1", operation_id="demo", name="Suporte N1"))
            if db.get(Queue, "n2") is None:
                db.add(Queue(id="n2", operation_id="demo", name="Suporte N2"))
            for oid, name in [("op-ana", "Ana (demonstração)"), ("op-bruno", "Bruno (demonstração)")]:
                if db.get(Operator, oid) is None:
                    db.add(Operator(id=oid, operation_id="demo", name=name,
                                    presence="AVAILABLE", capacity=1))
                if db.get(QueueMembership, ("n1", oid)) is None:
                    db.add(QueueMembership(queue_id="n1", operator_id=oid))
            if db.get(QueueMembership, ("n2", "op-bruno")) is None:
                db.add(QueueMembership(queue_id="n2", operator_id="op-bruno"))
        return {"result": "demo_ready", "operation_id": "demo", "queue_id": "n1"}

    @app.get("/v1/dashboard", dependencies=[Depends(authenticate)])
    def dashboard_snapshot():
        """One read for the local cockpit; excludes message bodies and outbox payloads."""
        with factory() as db:
            qs = db.scalars(select(Queue).order_by(Queue.id)).all()
            ops = db.scalars(select(Operator).order_by(Operator.name)).all()
            recent = db.scalars(
                select(HandoffSession)
                .order_by(HandoffSession.created_at.desc(), HandoffSession.id.desc())
                .limit(200)
            ).all()
            waiting_by_queue = dict(db.execute(
                select(HandoffSession.queue_id, func.count())
                .where(HandoffSession.status == "QUEUED")
                .group_by(HandoffSession.queue_id)
            ).all())
            offered_by_queue = dict(db.execute(
                select(HandoffSession.queue_id, func.count())
                .where(HandoffSession.status == "OFFERED")
                .group_by(HandoffSession.queue_id)
            ).all())
            active_by_queue = dict(db.execute(
                select(HandoffSession.queue_id, func.count())
                .where(HandoffSession.status == "ACTIVE")
                .group_by(HandoffSession.queue_id)
            ).all())
            active_by_operator = dict(db.execute(
                select(HandoffSession.operator_id, func.count())
                .where(HandoffSession.status == "ACTIVE")
                .group_by(HandoffSession.operator_id)
            ).all())
            offered_by_operator = dict(db.execute(
                select(HandoffSession.operator_id, func.count())
                .where(HandoffSession.status == "OFFERED")
                .group_by(HandoffSession.operator_id)
            ).all())
            outbox_by_status = dict(db.execute(
                select(OutboxEvent.status, func.count()).group_by(OutboxEvent.status)
            ).all())
            return {
                "handoffs": [as_handoff(h) for h in recent],
                "queues": [{"id": q.id, "operation_id": q.operation_id, "name": q.name,
                            "waiting": waiting_by_queue.get(q.id, 0),
                            "offered": offered_by_queue.get(q.id, 0),
                            "active": active_by_queue.get(q.id, 0)} for q in qs],
                "operators": [{"id": o.id, "operation_id": o.operation_id,
                               "name": o.name, "presence": o.presence,
                               "capacity": o.capacity,
                               "active": active_by_operator.get(o.id, 0),
                               "offered": offered_by_operator.get(o.id, 0)} for o in ops],
                "outbox": {
                    "total": sum(outbox_by_status.values()),
                    "pending": outbox_by_status.get("PENDING_ADAPTER", 0),
                },
            }

    @app.get("/v1/queues", dependencies=[Depends(authenticate)])
    def queues():
        with factory() as db:
            qs = db.scalars(select(Queue).order_by(Queue.id)).all()
            return [{"id": q.id, "operation_id": q.operation_id, "name": q.name,
                     "waiting": db.scalar(select(func.count()).select_from(HandoffSession).where(
                         HandoffSession.queue_id == q.id, HandoffSession.status == "QUEUED")) or 0} for q in qs]

    @app.get("/v1/operators", dependencies=[Depends(authenticate)])
    def operators():
        with factory() as db:
            ops = db.scalars(select(Operator).order_by(Operator.name)).all()
            return [{"id": o.id, "operation_id": o.operation_id, "name": o.name,
                     "presence": o.presence, "capacity": o.capacity,
                     "active": db.scalar(select(func.count()).select_from(HandoffSession).where(
                         HandoffSession.operator_id == o.id, HandoffSession.status == "ACTIVE")) or 0,
                     "offered": db.scalar(select(func.count()).select_from(HandoffSession).where(
                         HandoffSession.operator_id == o.id, HandoffSession.status == "OFFERED")) or 0} for o in ops]

    @app.patch("/v1/operators/{operator_id}/presence", dependencies=[Depends(authenticate)])
    def update_presence(operator_id: str, body: PresenceUpdate):
        with factory.begin() as db:
            op = db.get(Operator, operator_id)
            if op is None:
                raise HTTPException(404, "Operador inexistente")
            op.presence = body.presence
        return {"operator_id": operator_id, "presence": body.presence}

    @app.post("/v1/handoffs", status_code=201, dependencies=[Depends(authenticate)])
    def create_handoff(body: HandoffCreate, idempotency_key: str = Header(alias="Idempotency-Key")):
        if len(idempotency_key) < 8 or len(idempotency_key) > 128:
            raise HTTPException(422, "Idempotency-Key fora do limite 8–128")
        with factory() as db:
            exclusive_tx(db)
            existing = db.scalar(select(HandoffSession).where(
                HandoffSession.integration_id == body.integration_id,
                HandoffSession.idempotency_key == idempotency_key))
            if existing:
                if any([existing.operation_id != body.operation_id, existing.queue_id != body.queue_id,
                        existing.external_conversation_id != body.external_conversation_id,
                        existing.requester_label != body.requester_label, existing.subject != body.subject]):
                    raise HTTPException(409, "Chave de idempotência reutilizada com payload diferente")
                return as_handoff(existing)
            integration = db.get(Integration, body.integration_id)
            queue = db.get(Queue, body.queue_id)
            if (not integration or not queue or integration.operation_id != body.operation_id
                    or queue.operation_id != body.operation_id):
                raise HTTPException(422, "Operação, integração ou fila inválidas")
            h = HandoffSession(**body.model_dump(), idempotency_key=idempotency_key, status="QUEUED")
            db.add(h)
            db.flush()
            db.add(SessionEvent(session_id=h.id, event_type="QUEUED", actor=body.integration_id))
            db.commit()
            return as_handoff(h)

    @app.get("/v1/handoffs", dependencies=[Depends(authenticate)])
    def handoffs():
        with factory() as db:
            return [as_handoff(h) for h in db.scalars(select(HandoffSession).order_by(
                HandoffSession.created_at.desc(), HandoffSession.id.desc()).limit(200)).all()]

    @app.post("/v1/dispatch/next", dependencies=[Depends(authenticate)])
    def dispatch_next(body: DispatchRequest):
        with factory() as db:
            exclusive_tx(db)
            queue = db.get(Queue, body.queue_id)
            if not queue or queue.operation_id != body.operation_id:
                raise HTTPException(404, "Fila não encontrada")
            waiting = db.scalar(select(HandoffSession).where(
                HandoffSession.queue_id == body.queue_id, HandoffSession.status == "QUEUED"
            ).order_by(HandoffSession.created_at, HandoffSession.id).limit(1))
            if not waiting:
                db.commit()
                return {"result": "empty_queue"}
            operator_ids = db.scalars(select(QueueMembership.operator_id).where(
                QueueMembership.queue_id == body.queue_id)).all()
            for op in db.scalars(select(Operator).where(
                    Operator.id.in_(operator_ids), Operator.operation_id == body.operation_id,
                    Operator.presence == "AVAILABLE").order_by(Operator.id)).all():
                active_count = db.scalar(select(func.count()).select_from(HandoffSession).where(
                    HandoffSession.operator_id == op.id,
                    HandoffSession.status.in_(("ACTIVE", "OFFERED")))) or 0
                if active_count < op.capacity:
                    waiting.operator_id = op.id
                    waiting.status = "ACTIVE"
                    waiting.updated_at = utc_now()
                    db.add(SessionEvent(session_id=waiting.id, event_type="ACTIVE", actor=op.id))
                    db.commit()
                    return {"result": "assigned", "session": as_handoff(waiting)}
            db.commit()
            return {"result": "no_operator_available"}

    @app.get("/v1/handoffs/{handoff_id}/messages", dependencies=[Depends(authenticate)])
    def messages(handoff_id: str):
        with factory() as db:
            if not db.get(HandoffSession, handoff_id):
                raise HTTPException(404, "Atendimento não encontrado")
            msgs = db.scalars(select(Message).where(Message.session_id == handoff_id).order_by(
                Message.created_at, Message.id)).all()
            return [{"id": m.id, "sender": m.sender, "content": m.content,
                     "created_at": m.created_at.isoformat()} for m in msgs]

    @app.post("/v1/handoffs/{handoff_id}/messages", status_code=201, dependencies=[Depends(authenticate)])
    def add_message(handoff_id: str, body: MessageCreate):
        with factory() as db:
            exclusive_tx(db)
            h = db.get(HandoffSession, handoff_id)
            if h is None:
                raise HTTPException(404, "Atendimento não encontrado")
            if h.status not in {"QUEUED", "OFFERED", "ACTIVE"}:
                raise HTTPException(409, "Sessão não aceita mensagens")
            if body.sender == "OPERATOR" and h.status != "ACTIVE":
                raise HTTPException(409, "Operador ainda não atribuído")
            if (body.sender == "OPERATOR" and body.operator_id is not None
                    and body.operator_id != h.operator_id):
                raise HTTPException(403, "Operador não é responsável pelo atendimento")
            existing = db.scalar(select(Message).where(
                Message.session_id == handoff_id,
                Message.external_message_id == body.external_message_id))
            if existing:
                if existing.sender != body.sender or existing.content != body.content:
                    raise HTTPException(409, "Mensagem repetida com conteúdo diferente")
                return {"id": existing.id, "status": "duplicate"}
            m = Message(session_id=handoff_id, **body.model_dump(exclude={"operator_id"}))
            db.add(m)
            db.flush()
            if body.sender == "OPERATOR":
                db.add(OutboxEvent(session_id=handoff_id, message_id=m.id,
                                   destination_integration_id=h.integration_id, status="PENDING_ADAPTER"))
            db.commit()
            return {"id": m.id, "status": "recorded", "delivery": (
                "pending_adapter" if body.sender == "OPERATOR" else "internal")}

    @app.get("/v1/outbox", dependencies=[Depends(authenticate)])
    def outbox():
        with factory() as db:
            result = db.execute(select(OutboxEvent, Message).join(Message, Message.id == OutboxEvent.message_id)
                                .order_by(OutboxEvent.created_at).limit(100)).all()
            return [{"id": o.id, "session_id": o.session_id,
                     "integration_id": o.destination_integration_id,
                     "status": o.status, "content": m.content} for o, m in result]

    @app.post("/v1/handoffs/{handoff_id}/close", dependencies=[Depends(authenticate)])
    def close(handoff_id: str):
        with factory() as db:
            exclusive_tx(db)
            h = db.get(HandoffSession, handoff_id)
            if not h:
                raise HTTPException(404, "Atendimento não encontrado")
            if h.status == "CLOSED":
                db.commit()
                return as_handoff(h)
            if h.status != "ACTIVE":
                raise HTTPException(409, "Somente atendimento ativo pode ser concluído")
            h.status = "CLOSED"
            h.updated_at = utc_now()
            db.add(SessionEvent(session_id=h.id, event_type="CLOSED", actor=h.operator_id or "system"))
            db.commit()
            return as_handoff(h)

    app.include_router(register_operator_workflow(factory, authenticate, exclusive_tx, as_handoff))
    return app

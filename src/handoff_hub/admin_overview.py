"""SPEC-007/A0: read-only operation-scoped administration inventory.

This is a local POC administration projection, not a lifecycle mutation API.
No conversation content, bearer credentials or audit payloads are returned.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from handoff_hub.poc_db import (
    AuthUser,
    HandoffSession,
    Operation,
    Operator,
    Queue,
    QueueMembership,
    QueueRoleGrant,
)
from handoff_hub.queue_lifecycle import change_state, create_draft, queue_state
from handoff_hub.security_writer import record_security_decision


class NewQueue(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,39}$", max_length=40)
    name: str = Field(min_length=3, max_length=120)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        if name != name.strip() or any(ord(c) < 32 for c in name):
            raise ValueError("Nome deve ser legivel e sem espacos nas extremidades")
        return name


class StateChange(BaseModel):
    state: Literal["ACTIVE", "PAUSED", "ARCHIVED"]
    expected_version: int = Field(ge=0)


def register_admin_overview(
    factory, authenticate, *, security_audit_enabled: bool,
    lifecycle_enabled: bool = False,
) -> APIRouter:
    router = APIRouter()

    @router.get("/admin/overview", dependencies=[Depends(authenticate)])
    def overview(request: Request):
        principal = request.state.principal
        if principal.role != "ADMIN":
            raise HTTPException(403, "Inventario administrativo exige ADMIN")
        with factory() as db:
            operation = db.get(Operation, principal.operation_id)
            if operation is None:
                raise HTTPException(404, "Operacao indisponivel")
            queues = db.scalars(
                select(Queue).where(Queue.operation_id == principal.operation_id)
                .order_by(Queue.name, Queue.id)
            ).all()
            status_counts = defaultdict(dict)
            for queue_id, status, count in db.execute(
                select(HandoffSession.queue_id, HandoffSession.status, func.count())
                .where(HandoffSession.operation_id == principal.operation_id)
                .group_by(HandoffSession.queue_id, HandoffSession.status)
            ):
                status_counts[queue_id][status] = count
            memberships = dict(db.execute(
                select(QueueMembership.queue_id, func.count())
                .join(Queue, Queue.id == QueueMembership.queue_id)
                .where(Queue.operation_id == principal.operation_id)
                .group_by(QueueMembership.queue_id)
            ).all())
            grants = dict(db.execute(
                select(QueueRoleGrant.queue_id, func.count())
                .join(Queue, Queue.id == QueueRoleGrant.queue_id)
                .where(Queue.operation_id == principal.operation_id)
                .group_by(QueueRoleGrant.queue_id)
            ).all())
            rows = []
            for queue in queues:
                statuses = status_counts[queue.id]
                rows.append({
                    "id": queue.id,
                    "name": queue.name,
                    "members": memberships.get(queue.id, 0),
                    "grants": grants.get(queue.id, 0),
                    "waiting": statuses.get("QUEUED", 0),
                    "offered": statuses.get("OFFERED", 0),
                    "active": statuses.get("ACTIVE", 0),
                    "total_sessions": sum(statuses.values()),
                    "lifecycle_state": queue_state(db, queue.id, enabled=lifecycle_enabled)[0],
                    "lifecycle_version": queue_state(db, queue.id, enabled=lifecycle_enabled)[1],
                })
            operators = db.scalar(
                select(func.count()).select_from(Operator)
                .where(Operator.operation_id == principal.operation_id)
            ) or 0
            accounts = db.scalar(
                select(func.count()).select_from(AuthUser)
                .where(AuthUser.operation_id == principal.operation_id)
            ) or 0
            return {
                "operation": {"id": operation.id, "name": operation.name},
                "summary": {
                    "queues": len(rows),
                    "operators": operators,
                    "accounts": accounts,
                    "role_grants": sum(grants.values()),
                    "sessions_in_progress": sum(
                        row["waiting"] + row["offered"] + row["active"]
                        for row in rows
                    ),
                },
                "queues": rows,
                "capabilities": {
                    "read_only": True,
                    "queue_create_available": security_audit_enabled,
                    "queue_lifecycle_available": lifecycle_enabled,
                    "identity_provider": "LOCAL_POC",
                },
            }


    @router.get("/admin/people", dependencies=[Depends(authenticate)])
    def people(request: Request):
        """B1.0: read-only identity/operator/membership projection for one operation."""
        principal = request.state.principal
        if principal.role != "ADMIN":
            raise HTTPException(403, "Inventario de pessoas exige ADMIN")
        with factory() as db:
            operation = db.get(Operation, principal.operation_id)
            if operation is None:
                raise HTTPException(404, "Operacao indisponivel")
            operators = db.scalars(
                select(Operator)
                .where(Operator.operation_id == principal.operation_id)
                .order_by(Operator.name, Operator.id)
            ).all()
            operator_ids = {operator.id for operator in operators}
            memberships = defaultdict(list)
            for operator_id, queue_id, queue_name in db.execute(
                select(QueueMembership.operator_id, Queue.id, Queue.name)
                .join(Queue, Queue.id == QueueMembership.queue_id)
                .join(Operator, Operator.id == QueueMembership.operator_id)
                .where(
                    Queue.operation_id == principal.operation_id,
                    Operator.operation_id == principal.operation_id,
                )
                .order_by(Operator.id, Queue.name, Queue.id)
            ):
                memberships[operator_id].append({
                    "queue_id": queue_id,
                    "queue_name": queue_name,
                })
            occupancy = defaultdict(dict)
            for operator_id, status, count in db.execute(
                select(HandoffSession.operator_id, HandoffSession.status, func.count())
                .where(
                    HandoffSession.operation_id == principal.operation_id,
                    HandoffSession.operator_id.in_(operator_ids),
                    HandoffSession.status.in_(("ACTIVE", "OFFERED")),
                )
                .group_by(HandoffSession.operator_id, HandoffSession.status)
            ):
                occupancy[operator_id][status] = count
            accounts = db.scalars(
                select(AuthUser)
                .where(AuthUser.operation_id == principal.operation_id)
                .order_by(AuthUser.username, AuthUser.id)
            ).all()
            return {
                "operation": {"id": operation.id, "name": operation.name},
                "operators": [{
                    "id": operator.id,
                    "name": operator.name,
                    "presence": operator.presence,
                    "capacity": operator.capacity,
                    "active": occupancy[operator.id].get("ACTIVE", 0),
                    "offered": occupancy[operator.id].get("OFFERED", 0),
                    "memberships": memberships[operator.id],
                } for operator in operators],
                "accounts": [{
                    "id": account.id,
                    "username": account.username,
                    "role": account.role,
                    "is_active": account.is_active,
                    "operator_id": (
                        account.operator_id if account.operator_id in operator_ids
                        else None
                    ),
                } for account in accounts],
                "capabilities": {
                    "read_only": True,
                    "membership_write_available": False,
                    "grant_write_available": False,
                    "identity_provider": "LOCAL_POC",
                },
            }

    @router.post("/admin/queues", status_code=201, dependencies=[Depends(authenticate)])
    def create_queue(request: Request, body: NewQueue):
        principal = request.state.principal
        if principal.role != "ADMIN":
            raise HTTPException(403, "Cadastro de filas exige ADMIN")
        if not security_audit_enabled:
            raise HTTPException(503, "Cadastro indisponivel sem auditoria 006b4")
        try:
            with factory() as db:
                # SQLite POC: one writer owns ID check, insert and journal.
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                if db.get(Operation, principal.operation_id) is None:
                    raise HTTPException(404, "Operacao indisponivel")
                if db.get(Queue, body.id) is not None:
                    raise HTTPException(409, "Identificador de fila indisponivel")
                queue = Queue(
                    id=body.id, operation_id=principal.operation_id, name=body.name,
                )
                db.add(queue)
                db.flush()
                try:
                    record_security_decision(
                        db, principal, action="QUEUE_CREATED",
                        outcome="APPLIED", queue_id=queue.id,
                    )
                    create_draft(
                        db, queue.id, principal.operation_id, principal.user_id,
                        enabled=lifecycle_enabled,
                    )
                except SQLAlchemyError as exc:
                    # The queue INSERT must roll back with the failed journal.
                    raise HTTPException(
                        503, "Auditoria indisponivel: cadastro nao aplicado",
                    ) from exc
                db.commit()
                return {"id": queue.id, "name": queue.name,
                        "operation_id": principal.operation_id,
                        "audit": "APPLIED"}
        except IntegrityError as exc:
            raise HTTPException(409, "Cadastro de fila em conflito") from exc

    @router.patch("/admin/queues/{queue_id}/state",
                  dependencies=[Depends(authenticate)])
    def update_queue_state(request: Request, queue_id: str, body: StateChange):
        principal = request.state.principal
        if principal.role != "ADMIN":
            raise HTTPException(403, "Alteracao de fila exige ADMIN")
        if not lifecycle_enabled or not security_audit_enabled:
            raise HTTPException(503, "Ciclo de vida exige schema 007a2")
        try:
            with factory() as db:
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                queue = db.get(Queue, queue_id)
                if queue is None or queue.operation_id != principal.operation_id:
                    raise HTTPException(404, "Fila nao encontrada")
                try:
                    response = change_state(
                        db, queue.id, principal.operation_id, principal.user_id,
                        body.state, body.expected_version,
                    )
                except SQLAlchemyError as exc:
                    raise HTTPException(503, "Auditoria do estado indisponivel") from exc
                db.commit()
                return response
        except IntegrityError as exc:
            raise HTTPException(503, "Transicao nao persistida") from exc

    return router

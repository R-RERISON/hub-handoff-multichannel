"""Explicit per-queue grants for human supervisory/audit access (SPEC-006A).

Current-queue scope only. Historical cross-queue message visibility is deliberately
denied until session segments can be migrated and authorized precisely.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from handoff_hub.poc_db import (
    AuthUser,
    HandoffSession,
    Queue,
    QueueMembership,
    QueueRoleGrant,
    SessionTransfer,
)

SCOPED_ROLES = frozenset({"SUPERVISOR", "AUDITOR"})


def granted_queues(db: Session, principal) -> set[str]:
    if principal.role == "ADMIN":
        return set(db.scalars(
            select(Queue.id).where(Queue.operation_id == principal.operation_id)
        ).all())
    if principal.role == "OPERATOR":
        if not principal.operator_id:
            return set()
        return set(db.scalars(
            select(QueueMembership.queue_id)
            .join(Queue, Queue.id == QueueMembership.queue_id)
            .where(
                QueueMembership.operator_id == principal.operator_id,
                Queue.operation_id == principal.operation_id,
            )
        ).all())
    return set(db.scalars(
        select(QueueRoleGrant.queue_id)
        .join(Queue, Queue.id == QueueRoleGrant.queue_id)
        .where(
            QueueRoleGrant.user_id == principal.user_id,
            QueueRoleGrant.role == principal.role,
            Queue.operation_id == principal.operation_id,
        )
    ).all())


def require_queue(db: Session, principal, queue_id: str, *, manage: bool = False) -> None:
    queue = db.get(Queue, queue_id)
    if queue is None or queue.operation_id != principal.operation_id:
        raise HTTPException(404, "Fila não encontrada")
    if principal.role == "ADMIN":
        return
    if principal.role != "SUPERVISOR" and manage:
        raise HTTPException(403, "Sem permissão para gerenciar fila")
    if principal.role not in SCOPED_ROLES or queue_id not in granted_queues(db, principal):
        raise HTTPException(404, "Fila não encontrada")


def require_handoff(db: Session, principal, handoff_id: str) -> HandoffSession:
    handoff = db.get(HandoffSession, handoff_id)
    if handoff is None or handoff.operation_id != principal.operation_id:
        raise HTTPException(404, "Atendimento não encontrado")
    if principal.role in SCOPED_ROLES:
        require_queue(db, principal, handoff.queue_id)
        # Fail closed on cross-queue history until message-level segments exist.
        if db.scalar(select(SessionTransfer.id).where(
            SessionTransfer.session_id == handoff_id
        ).limit(1)) is not None:
            raise HTTPException(
                403, "Histórico transferido exige autorização por segmento"
            )
    return handoff


def change_grant(db: Session, actor, user_id: str, queue_id: str,
                 role: str, enabled: bool) -> dict:
    if actor.role != "ADMIN":
        raise HTTPException(403, "Somente administrador gerencia concessões")
    if role not in SCOPED_ROLES:
        raise HTTPException(422, "Papel incompatível com concessão por fila")
    user = db.get(AuthUser, user_id)
    queue = db.get(Queue, queue_id)
    if user is None or queue is None or user.operation_id != queue.operation_id:
        raise HTTPException(404, "Usuário ou fila não encontrados")
    if user.role != role:
        raise HTTPException(422, "Papel não corresponde à identidade")
    if actor.operation_id != queue.operation_id:
        raise HTTPException(403, "Operação fora do escopo do administrador")
    grant = db.get(QueueRoleGrant, (user_id, queue_id, role))
    if enabled and grant is None:
        db.add(QueueRoleGrant(user_id=user_id, queue_id=queue_id, role=role,
                              granted_by=actor.user_id))
    elif not enabled and grant is not None:
        db.delete(grant)
    db.flush()
    return {"user_id": user_id, "queue_id": queue_id, "role": role,
            "enabled": enabled}

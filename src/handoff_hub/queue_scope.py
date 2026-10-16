"""SPEC-006A: queue-scoped authorization shared by API reads and writes.

A queue membership controls dispatch eligibility; QueueRoleGrant controls
read/write authorization. These are intentionally separate security domains.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from handoff_hub.poc_db import (
    HandoffSession,
    Operator,
    Queue,
    QueueMembership,
    QueueRoleGrant,
    SessionTransfer,
)

SCOPED_ROLES = frozenset({"SUPERVISOR", "AUDITOR"})


def permitted_queues(db: Session, principal) -> set[str]:
    """Return current, operation-bounded queue grants from live SQL state."""
    if principal.role == "ADMIN":
        return set(db.scalars(select(Queue.id).where(
            Queue.operation_id == principal.operation_id
        )).all())
    if principal.role in SCOPED_ROLES:
        return set(db.scalars(
            select(QueueRoleGrant.queue_id)
            .join(Queue, Queue.id == QueueRoleGrant.queue_id)
            .where(
                QueueRoleGrant.user_id == principal.user_id,
                QueueRoleGrant.role == principal.role,
                Queue.operation_id == principal.operation_id,
            )
        ).all())
    if principal.role == "OPERATOR" and principal.operator_id:
        return set(db.scalars(
            select(QueueMembership.queue_id)
            .join(Queue, Queue.id == QueueMembership.queue_id)
            .where(
                QueueMembership.operator_id == principal.operator_id,
                Queue.operation_id == principal.operation_id,
            )
        ).all())
    return set()


def require_queue(db: Session, principal, queue_id: str) -> None:
    if queue_id not in permitted_queues(db, principal):
        # Do not reveal if a resource in another queue exists.
        raise HTTPException(404, "Fila não encontrada")


def require_handoff(db: Session, principal, handoff_id: str) -> HandoffSession:
    h = db.get(HandoffSession, handoff_id)
    if h is None or h.operation_id != principal.operation_id:
        raise HTTPException(404, "Atendimento não encontrado")
    if principal.role == "OPERATOR":
        if h.operator_id != principal.operator_id:
            raise HTTPException(404, "Atendimento não encontrado")
    else:
        allowed = permitted_queues(db, principal)
        require_queue(db, principal, h.queue_id)
        if principal.role in SCOPED_ROLES:
            # Until messages/events are backfilled with explicit queue segments,
            # deny the entire content/timeline of a transferred session unless
            # *all* its historical queues are granted. Never leak N1 via N2.
            route = db.execute(
                select(SessionTransfer.from_queue_id, SessionTransfer.to_queue_id)
                .where(SessionTransfer.session_id == handoff_id)
            ).all()
            if any(
                from_queue not in allowed or to_queue not in allowed
                for from_queue, to_queue in route
            ):
                raise HTTPException(404, "Atendimento não encontrado")
    return h


def require_operator_management(db: Session, principal, operator_id: str) -> None:
    """Global capacity/presence changes affect all the operator's queues.

    A supervisor needs grants to *every* associated queue; otherwise changing
    the global field would affect another supervisor's queue implicitly.
    """
    op = db.get(Operator, operator_id)
    if op is None or op.operation_id != principal.operation_id:
        raise HTTPException(404, "Operador não encontrado")
    if principal.role == "ADMIN":
        return
    if principal.role != "SUPERVISOR":
        raise HTTPException(403, "Gestão indisponível para este perfil")
    memberships = set(db.scalars(select(QueueMembership.queue_id).where(
        QueueMembership.operator_id == operator_id
    )).all())
    if not memberships or not memberships.issubset(permitted_queues(db, principal)):
        raise HTTPException(403, "Operador vinculado a outra fila")


def visible_operator_ids(db: Session, principal) -> set[str]:
    queues = permitted_queues(db, principal)
    if not queues:
        return set()
    return set(db.scalars(select(QueueMembership.operator_id).where(
        QueueMembership.queue_id.in_(queues)
    )).all())

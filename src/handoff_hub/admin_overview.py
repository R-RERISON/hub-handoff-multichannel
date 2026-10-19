"""SPEC-007/A0: read-only operation-scoped administration inventory.

This is a local POC administration projection, not a lifecycle mutation API.
No conversation content, bearer credentials or audit payloads are returned.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select

from handoff_hub.poc_db import (
    AuthUser,
    HandoffSession,
    Operation,
    Operator,
    Queue,
    QueueMembership,
    QueueRoleGrant,
)


def register_admin_overview(factory, authenticate) -> APIRouter:
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
                    "queue_lifecycle_available": False,
                    "identity_provider": "LOCAL_POC",
                },
            }

    return router

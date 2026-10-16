"""Grant management: only platform admins can delegate queue-scoped roles."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from handoff_hub.poc_db import AuthUser, Queue, QueueRoleGrant
from handoff_hub.queue_scope import permitted_queues


class GrantInput(BaseModel):
    user_id: str
    queue_id: str
    role: Literal["SUPERVISOR", "AUDITOR"]


def register_queue_grants(factory, authenticate):
    router = APIRouter(prefix="/v1", tags=["Queue authorization"])

    @router.get("/me/queues")
    def my_queues(principal=Depends(authenticate)):
        with factory() as db:
            allowed = permitted_queues(db, principal)
            queues = db.scalars(
                select(Queue).where(
                    Queue.operation_id == principal.operation_id,
                    Queue.id.in_(allowed),
                ).order_by(Queue.name)
            ).all()
            return [{"id": q.id, "operation_id": q.operation_id, "name": q.name}
                    for q in queues]

    def admin_only(principal):
        if principal.role != "ADMIN":
            raise HTTPException(403, "Somente administrador pode delegar acesso")

    @router.get("/admin/queue-grants")
    def list_grants(principal=Depends(authenticate)):
        admin_only(principal)
        with factory() as db:
            result = db.execute(
                select(QueueRoleGrant, AuthUser.username)
                .join(AuthUser, AuthUser.id == QueueRoleGrant.user_id)
                .join(Queue, Queue.id == QueueRoleGrant.queue_id)
                .where(Queue.operation_id == principal.operation_id,
                       AuthUser.operation_id == principal.operation_id)
                .order_by(QueueRoleGrant.queue_id, AuthUser.username)
            ).all()
            return [{
                "user_id": grant.user_id,
                "username": username,
                "queue_id": grant.queue_id,
                "role": grant.role,
                "granted_by": grant.granted_by,
            } for grant, username in result]

    @router.post("/admin/queue-grants", status_code=201)
    def grant(body: GrantInput, principal=Depends(authenticate)):
        admin_only(principal)
        with factory() as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            user = db.get(AuthUser, body.user_id)
            queue = db.get(Queue, body.queue_id)
            if (user is None or queue is None
                    or user.operation_id != principal.operation_id
                    or queue.operation_id != principal.operation_id
                    or user.role != body.role):
                raise HTTPException(422, "Usuário ou fila incompatível com o perfil")
            existing = db.get(QueueRoleGrant, (body.user_id, body.queue_id, body.role))
            if existing is not None:
                db.commit()
                return {"status": "already_granted", **body.model_dump()}
            db.add(QueueRoleGrant(
                user_id=user.id,
                queue_id=queue.id,
                role=body.role,
                granted_by=principal.username,
            ))
            db.commit()
        return {"status": "granted", **body.model_dump()}

    @router.delete("/admin/queue-grants/{user_id}/{queue_id}/{role}")
    def revoke(user_id: str, queue_id: str, role: str,
               principal=Depends(authenticate)):
        admin_only(principal)
        with factory() as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            grant = db.get(QueueRoleGrant, (user_id, queue_id, role))
            if grant is None:
                raise HTTPException(404, "Concessão não encontrada")
            queue = db.get(Queue, queue_id)
            user = db.get(AuthUser, user_id)
            if (queue is None or user is None
                    or queue.operation_id != principal.operation_id
                    or user.operation_id != principal.operation_id):
                raise HTTPException(404, "Concessão não encontrada")
            db.delete(grant)
            db.commit()
            return {"status": "revoked"}

    return router

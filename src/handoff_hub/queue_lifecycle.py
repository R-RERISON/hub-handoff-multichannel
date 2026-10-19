"""SPEC-007/A1.2: lifecycle semantics on migration-owned tables (SQLite POC).

Absent rows represent pre-migration queues, kept ACTIVE for compatibility.
New queues created AFTER the explicit opt-in migration begin as DRAFT.
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from handoff_hub.poc_db import HandoffSession, utc_now
from handoff_hub.queue_lifecycle_schema import (
    QUEUE_LIFECYCLE,
    QUEUE_LIFECYCLE_EVENTS,
)

TRANSITIONS = {
    "DRAFT": frozenset({"ACTIVE", "ARCHIVED"}),
    "ACTIVE": frozenset({"PAUSED"}),
    "PAUSED": frozenset({"ACTIVE", "ARCHIVED"}),
    "ARCHIVED": frozenset(),
}
BUSY = ("QUEUED", "OFFERED", "ACTIVE")


def queue_state(db: Session, queue_id: str, *, enabled: bool) -> tuple[str, int]:
    if not enabled:
        return ("ACTIVE", 0)
    row = db.execute(
        select(QUEUE_LIFECYCLE.c.state, QUEUE_LIFECYCLE.c.version)
        .where(QUEUE_LIFECYCLE.c.queue_id == queue_id)
    ).first()
    return (row.state, row.version) if row is not None else ("ACTIVE", 0)


def queue_active(db: Session, queue_id: str, *, enabled: bool) -> bool:
    return queue_state(db, queue_id, enabled=enabled)[0] == "ACTIVE"


def require_active(db: Session, queue_id: str, *, enabled: bool) -> None:
    if not queue_active(db, queue_id, enabled=enabled):
        raise HTTPException(409, "Fila indisponivel para novas entradas/ofertas")


def create_draft(db: Session, queue_id: str, operation_id: str,
                 actor_id: str, *, enabled: bool) -> None:
    if not enabled:
        return
    now = utc_now()
    db.execute(insert(QUEUE_LIFECYCLE).values(
        queue_id=queue_id, state="DRAFT", version=1,
        changed_at=now, changed_by=actor_id,
    ))
    db.execute(insert(QUEUE_LIFECYCLE_EVENTS).values(
        id=str(uuid4()), queue_id=queue_id, operation_id=operation_id,
        actor_user_id=actor_id, from_state=None, to_state="DRAFT",
        version=1, created_at=now,
    ))


def change_state(db: Session, queue_id: str, operation_id: str, actor_id: str,
                 desired: str, expected_version: int) -> dict:
    """Caller must own BEGIN IMMEDIATE before reading queue state."""
    current, version = queue_state(db, queue_id, enabled=True)
    if expected_version != version:
        raise HTTPException(409, "Versao desatualizada: atualize o inventario")
    if desired not in TRANSITIONS[current]:
        raise HTTPException(409, "Transicao de estado nao autorizada")
    if desired in ("PAUSED", "ARCHIVED"):
        count = db.scalar(
            select(func.count()).select_from(HandoffSession)
            .where(HandoffSession.queue_id == queue_id,
                   HandoffSession.status.in_(BUSY))
        ) or 0
        if count:
            raise HTTPException(
                409, "Fila tem atendimentos pendentes, ofertados ou ativos",
            )
    new_version = version + 1
    now = utc_now()
    if version == 0:
        db.execute(insert(QUEUE_LIFECYCLE).values(
            queue_id=queue_id, state=desired, version=new_version,
            changed_at=now, changed_by=actor_id,
        ))
    else:
        changed = db.execute(
            update(QUEUE_LIFECYCLE)
            .where(QUEUE_LIFECYCLE.c.queue_id == queue_id,
                   QUEUE_LIFECYCLE.c.version == version)
            .values(state=desired, version=new_version,
                    changed_at=now, changed_by=actor_id)
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Versao alterada em outra transacao")
    db.execute(insert(QUEUE_LIFECYCLE_EVENTS).values(
        id=str(uuid4()), queue_id=queue_id, operation_id=operation_id,
        actor_user_id=actor_id, from_state=current, to_state=desired,
        version=new_version, created_at=now,
    ))
    return {"queue_id": queue_id, "operation_id": operation_id,
            "previous_state": current, "state": desired,
            "version": new_version, "audit": "APPLIED"}

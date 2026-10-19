"""SPEC-006B-5.2: minimal security-decision journal.

Successful grant changes are recorded in the SAME transaction as the grant.
Authenticated scoped-history denials are recorded in a separate transaction
because the read transaction is rolled back on HTTP 403/404. Denials preserve
the original status even if the security journal becomes unavailable.
"""
import logging
from functools import wraps
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import insert
from sqlalchemy.orm import Session

from handoff_hub.poc_db import Queue, utc_now
from handoff_hub.security_schema import SECURITY_DECISIONS

LOGGER = logging.getLogger("handoff.security")
ACTIONS = frozenset({
    "HISTORY_LIST_DENIED", "HISTORY_DETAIL_DENIED",
    "GRANT_ENABLED", "GRANT_REVOKED", "QUEUE_CREATED",
})


def record_security_decision(
    db: Session, principal, *,
    action: str, outcome: str,
    queue_id: str | None,
    target_user_id: str | None = None,
) -> None:
    """No request body, response body, source session, credentials or PII."""
    if action not in ACTIONS or outcome not in ("DENIED", "APPLIED"):
        raise ValueError("Unsupported security event")
    db.execute(insert(SECURITY_DECISIONS).values(
        id=str(uuid4()), actor_user_id=principal.user_id,
        actor_role=principal.role, operation_id=principal.operation_id,
        queue_id=queue_id, target_user_id=target_user_id,
        action=action, outcome=outcome, created_at=utc_now(),
    ))


def record_scoped_denial(factory, principal, *, queue_id: str, resource: str) -> None:
    """Best-effort separate write after rollback; never disclose hidden queue IDs."""
    if resource not in ("LIST", "DETAIL"):
        raise ValueError("Unsupported protected read")
    try:
        with factory.begin() as db:
            # Unknown or cross-operation queue names are never persisted.
            queue = db.get(Queue, queue_id)
            known_id = (
                queue_id if queue is not None
                and queue.operation_id == principal.operation_id else None
            )
            record_security_decision(
                db, principal, action=f"HISTORY_{resource}_DENIED",
                outcome="DENIED", queue_id=known_id,
            )
    # This is an intentional fail-open-for-logging boundary, NOT for authorization:
    # a broken audit hook must never turn an already-denied 403/404 into HTTP 500.
    except Exception:  # noqa: BLE001
        # Do not log query parameters, identifiers, exception text or SQL values.
        LOGGER.error("Security decision audit persistence unavailable")


def journal_denials(factory, provenance, *, resource: str):
    """Decorate FastAPI endpoint with original signature preserved for DI."""
    def decorate(endpoint):
        @wraps(endpoint)
        def guarded(*args, **kwargs):
            try:
                return endpoint(*args, **kwargs)
            except HTTPException as exc:
                if exc.status_code in (403, 404) and provenance.security_audit_enabled:
                    request = kwargs.get("request")
                    principal = getattr(getattr(request, "state", None), "principal", None)
                    queue_id = kwargs.get("queue_id")
                    if principal is not None and isinstance(queue_id, str):
                        record_scoped_denial(
                            factory, principal, queue_id=queue_id, resource=resource,
                        )
                raise
        return guarded
    return decorate

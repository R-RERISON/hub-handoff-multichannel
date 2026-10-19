"""SPEC-006B-5.1: durable, payload-free journal of successful verified reads.

The caller MUST persist this row in the same transaction as the protected
database read, before returning any protected data to the HTTP client.
No UPDATE or DELETE operation is exposed through this module.
"""
from uuid import uuid4

from sqlalchemy import insert
from sqlalchemy.orm import Session

from handoff_hub.audit_schema import HISTORY_ACCESS_AUDIT
from handoff_hub.poc_db import utc_now


def record_verified_read(
    db: Session, principal, *,
    resource: str,
    queue_id: str,
    session_id: str | None,
    page_size: int,
    message_page: int | None = None,
    event_page: int | None = None,
    returned_messages: int = 0,
    returned_events: int = 0,
    returned_sessions: int = 0,
) -> None:
    """Log only scope, counts and authenticated actor, NEVER message content."""
    if resource not in {"LIST", "DETAIL"}:
        raise ValueError("Unsupported verified history audit resource")
    db.execute(insert(HISTORY_ACCESS_AUDIT).values(
        id=str(uuid4()),
        user_id=principal.user_id,
        role=principal.role,
        operation_id=principal.operation_id,
        queue_id=queue_id,
        session_id=session_id,
        resource=resource,
        page_size=page_size,
        message_page=message_page,
        event_page=event_page,
        returned_messages=returned_messages,
        returned_events=returned_events,
        returned_sessions=returned_sessions,
        created_at=utc_now(),
    ))

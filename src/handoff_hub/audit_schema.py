"""SPEC-006B-5.1: migration-owned access journal for verified history only.

Not registered in POC Base.metadata: ordinary POC startup never creates it.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, MetaData, String, Table

AUDIT_METADATA = MetaData()
for _name in ("auth_users", "queues", "handoff_sessions"):
    Table(_name, AUDIT_METADATA, Column("id", String(40), primary_key=True))

HISTORY_ACCESS_AUDIT = Table(
    "history_access_audit", AUDIT_METADATA,
    Column("id", String(40), primary_key=True),
    Column("user_id", String(40), ForeignKey("auth_users.id"), nullable=False),
    Column("role", String(16), nullable=False),
    Column("operation_id", String(40), nullable=False),
    Column("queue_id", String(60), ForeignKey("queues.id"), nullable=False),
    Column("session_id", String(40), ForeignKey("handoff_sessions.id"), nullable=True),
    Column("resource", String(16), nullable=False),
    Column("message_page", Integer, nullable=True),
    Column("event_page", Integer, nullable=True),
    Column("page_size", Integer, nullable=False),
    Column("returned_messages", Integer, nullable=False),
    Column("returned_events", Integer, nullable=False),
    Column("returned_sessions", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_history_audit_scope_time", "operation_id", "queue_id", "created_at"),
    Index("ix_history_audit_user_time", "user_id", "created_at"),
)

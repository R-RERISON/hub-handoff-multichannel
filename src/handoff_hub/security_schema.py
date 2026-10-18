"""SPEC-006B-5.2: journal of scoped access denials and grant changes.

Separate migration-owned table: never imported into POC Base.metadata.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Index, MetaData, String, Table

SECURITY_METADATA = MetaData()
for _name in ("auth_users", "queues"):
    Table(_name, SECURITY_METADATA, Column("id", String(40), primary_key=True))

SECURITY_DECISIONS = Table(
    "security_decisions", SECURITY_METADATA,
    Column("id", String(40), primary_key=True),
    Column("actor_user_id", String(40), ForeignKey("auth_users.id"), nullable=False),
    Column("actor_role", String(16), nullable=False),
    Column("operation_id", String(40), nullable=False),
    Column("queue_id", String(60), ForeignKey("queues.id"), nullable=True),
    Column("target_user_id", String(40), ForeignKey("auth_users.id"), nullable=True),
    Column("action", String(32), nullable=False),
    Column("outcome", String(16), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_security_decisions_operation_time", "operation_id", "created_at"),
    Index("ix_security_decisions_actor_time", "actor_user_id", "created_at"),
)

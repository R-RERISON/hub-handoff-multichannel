"""SPEC-007 lifecycle tables owned exclusively by 007a2 migration."""
from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Index,
    Integer, MetaData, String, Table,
)

LIFECYCLE_REVISION = "007a2_queue_lifecycle"
metadata = MetaData()
Table("queues", metadata, Column("id", String(60), primary_key=True))
Table("auth_users", metadata, Column("id", String(40), primary_key=True))

QUEUE_LIFECYCLE = Table(
    "queue_lifecycle", metadata,
    Column("queue_id", String(60), ForeignKey("queues.id"), primary_key=True),
    Column("state", String(16), nullable=False),
    Column("version", Integer, nullable=False),
    Column("changed_at", DateTime(timezone=True), nullable=False),
    Column("changed_by", String(40), ForeignKey("auth_users.id"), nullable=False),
    CheckConstraint("state IN ('DRAFT','ACTIVE','PAUSED','ARCHIVED')",
                    name="ck_queue_lifecycle_state"),
    CheckConstraint("version >= 1", name="ck_queue_lifecycle_version"),
)

QUEUE_LIFECYCLE_EVENTS = Table(
    "queue_lifecycle_events", metadata,
    Column("id", String(40), primary_key=True),
    Column("queue_id", String(60), ForeignKey("queues.id"), nullable=False),
    Column("operation_id", String(40), nullable=False),
    Column("actor_user_id", String(40), ForeignKey("auth_users.id"), nullable=False),
    Column("from_state", String(16), nullable=True),
    Column("to_state", String(16), nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_lifecycle_events_queue_time", "queue_id", "created_at"),
    Index("ix_lifecycle_events_operation_time", "operation_id", "created_at"),
)

LIFECYCLE_TABLES = (QUEUE_LIFECYCLE, QUEUE_LIFECYCLE_EVENTS)

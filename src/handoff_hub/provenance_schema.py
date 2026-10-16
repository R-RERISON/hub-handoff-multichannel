"""Schema contract for SPEC-006B-2 queue provenance; not registered on POC Base.

The deliberate separate metadata avoids Base.metadata.create_all() silently
creating migration-owned tables during an ordinary start.cmd launch.
This module supplies schema validation and Core table objects to the guarded
runtime recorder. It is intentionally NOT part of Base.metadata.create_all().
"""
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

PROVENANCE_METADATA = MetaData()
for _table in ("handoff_sessions", "queues", "session_transfers", "messages", "session_events"):
    Table(_table, PROVENANCE_METADATA, Column("id", String(40), primary_key=True))

SESSION_QUEUE_SEGMENTS = Table(
    "session_queue_segments", PROVENANCE_METADATA,
    Column("id", String(40), primary_key=True),
    Column("session_id", String(40), ForeignKey("handoff_sessions.id"), nullable=False),
    Column("queue_id", String(60), ForeignKey("queues.id"), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("ended_at", DateTime(timezone=True), nullable=True),
    Column("transfer_id", String(40), ForeignKey("session_transfers.id"), nullable=True),
    Column("provenance_state", String(16), nullable=False),
    UniqueConstraint("session_id", "ordinal", name="uq_session_queue_segment_order"),
    Index("ix_segments_queue_started", "queue_id", "started_at"),
    Index("ix_segments_session_order", "session_id", "ordinal"),
)

MESSAGE_QUEUE_PROVENANCE = Table(
    "message_queue_provenance", PROVENANCE_METADATA,
    Column("message_id", String(40), ForeignKey("messages.id"), primary_key=True),
    Column("segment_id", String(40), ForeignKey("session_queue_segments.id"), nullable=True),
    Column("assigned_by", String(16), nullable=False),
    Column("confidence", String(16), nullable=False),
    Index("ix_message_provenance_segment", "segment_id"),
)

SESSION_EVENT_QUEUE_PROVENANCE = Table(
    "session_event_queue_provenance", PROVENANCE_METADATA,
    Column("event_id", String(40), ForeignKey("session_events.id"), primary_key=True),
    Column("segment_id", String(40), ForeignKey("session_queue_segments.id"), nullable=True),
    Column("assigned_by", String(16), nullable=False),
    Column("confidence", String(16), nullable=False),
    Index("ix_event_provenance_segment", "segment_id"),
)

PROVENANCE_TABLES = (
    SESSION_QUEUE_SEGMENTS, MESSAGE_QUEUE_PROVENANCE, SESSION_EVENT_QUEUE_PROVENANCE,
)

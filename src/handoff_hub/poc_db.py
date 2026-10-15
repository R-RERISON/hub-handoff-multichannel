"""SQLite proof-of-concept schema, intentionally independent of Teams and legacy systems."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, create_engine, event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Operation(Base):
    __tablename__ = "operations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Integration(Base):
    __tablename__ = "integrations"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="simulator")
    __table_args__ = (Index("ix_integrations_operation", "operation_id"),)


class Queue(Base):
    __tablename__ = "queues"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    __table_args__ = (Index("ix_queues_operation", "operation_id"),)


class Operator(Base):
    __tablename__ = "operators"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    presence: Mapped[str] = mapped_column(String(20), nullable=False, default="AVAILABLE")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (CheckConstraint("capacity >= 1", name="ck_operator_capacity"),)


class QueueMembership(Base):
    __tablename__ = "queue_memberships"
    queue_id: Mapped[str] = mapped_column(ForeignKey("queues.id"), primary_key=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"), primary_key=True)


class HandoffSession(Base):
    __tablename__ = "handoff_sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=make_id)
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"), nullable=False)
    integration_id: Mapped[str] = mapped_column(ForeignKey("integrations.id"), nullable=False)
    queue_id: Mapped[str] = mapped_column(ForeignKey("queues.id"), nullable=False)
    external_conversation_id: Mapped[str] = mapped_column(String(200), nullable=False)
    requester_label: Mapped[str] = mapped_column(String(120), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="QUEUED")
    operator_id: Mapped[str | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (
        UniqueConstraint("integration_id", "idempotency_key", name="uq_handoff_request_key"),
        Index("ix_handoffs_queue_status", "queue_id", "status", "created_at"),
        Index("ix_handoffs_operator_status", "operator_id", "status"),
    )


class SessionEvent(Base):
    __tablename__ = "session_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=make_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("handoff_sessions.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (Index("ix_session_events_session", "session_id", "created_at"),)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=make_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("handoff_sessions.id"), nullable=False)
    sender: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    external_message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (
        UniqueConstraint("session_id", "external_message_id", name="uq_message_external_id"),
        Index("ix_messages_session", "session_id", "created_at"),
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=make_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("handoff_sessions.id"), nullable=False)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), nullable=False, unique=True)
    destination_integration_id: Mapped[str] = mapped_column(ForeignKey("integrations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING_ADAPTER")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


def make_session_factory(database_url: str):
    """SQLite single-node POC: SQLite serializes writers; SQL Server needs another strategy."""
    engine = create_engine(database_url, connect_args={"timeout": 10}, future=True)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=10000")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False), engine

"""SQLite proof-of-concept schema, intentionally independent of Teams and legacy systems."""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utc_now() -> datetime:
    return datetime.now(UTC)


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



class HandoffOffer(Base):
    """Durable operator offers; existing SQLite files gain this table via create_all."""

    __tablename__ = "handoff_offers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=make_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("handoff_sessions.id"), nullable=False
    )
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index("ix_offers_operator_status", "operator_id", "status"),
        Index("ix_offers_session_status", "session_id", "status"),
    )


class SessionTransfer(Base):
    """Transfer provenance without overwriting the original operator and queue."""

    __tablename__ = "session_transfers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=make_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("handoff_sessions.id"), nullable=False
    )
    from_queue_id: Mapped[str] = mapped_column(ForeignKey("queues.id"), nullable=False)
    to_queue_id: Mapped[str] = mapped_column(ForeignKey("queues.id"), nullable=False)
    from_operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (Index("ix_transfers_session", "session_id", "created_at"),)




class AuthUser(Base):
    """Local POC identity, never reused as the Teams bot credential."""

    __tablename__ = "auth_users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=make_id)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"), nullable=False)
    operator_id: Mapped[str | None] = mapped_column(ForeignKey("operators.id"))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)



class QueueRoleGrant(Base):
    """Authorization by queue, independent of dispatch membership.

    A principal can hold grants in several queues. Grants are checked against
    live database state at every request; a UI filter is never authoritative.
    """

    __tablename__ = "queue_role_grants"
    user_id: Mapped[str] = mapped_column(ForeignKey("auth_users.id"), primary_key=True)
    queue_id: Mapped[str] = mapped_column(ForeignKey("queues.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(24), primary_key=True)
    granted_by: Mapped[str] = mapped_column(String(80), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (Index("ix_queue_role_grants_queue_role", "queue_id", "role"),)



class AuthSession(Base):
    """Opaque bearer token is SHA-256 hashed; no plaintext tokens in SQLite."""

    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=make_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)
    __table_args__ = (
        Index("ix_auth_sessions_user", "user_id", "expires_at"),
        Index("ix_auth_sessions_heartbeat", "last_seen", "revoked"),
    )



class LoginThrottle(Base):
    """Persistence-backed local login lockout; external IAM replaces this in production."""

    __tablename__ = "login_throttles"
    username: Mapped[str] = mapped_column(String(80), primary_key=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))




class DemoSeedRevision(Base):
    """Apply baseline demo routing changes only once per SQLite database."""

    __tablename__ = "demo_seed_revisions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)



class DispatchTurn(Base):
    """Queue-scoped round-robin position, durable across service restarts."""

    __tablename__ = "dispatch_turns"
    queue_id: Mapped[str] = mapped_column(ForeignKey("queues.id"), primary_key=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"), primary_key=True)
    last_offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_offers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


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

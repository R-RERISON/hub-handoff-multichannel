"""Snapshot of the POC 0.5 base tables for fresh databases.

For existing populated POC 0.5 SQLite files, db_migrations marks this
baseline as applied after validating the existing table set and backing up
the database. Future schema changes MUST use explicit Alembic operations.
"""
from alembic import op

from handoff_hub.poc_db import Base

revision = "0001_poc_baseline"
down_revision = None
branch_labels = None
depends_on = None

BASE_TABLES = (
    "operations", "integrations", "queues", "operators",
    "queue_memberships", "handoff_sessions", "session_events",
    "messages", "outbox_events", "handoff_offers", "session_transfers",
    "auth_users", "auth_sessions", "login_throttles",
    "demo_seed_revisions", "dispatch_turns",
)


def upgrade() -> None:
    # Fixed table inventory prevents the initial migration from creating
    # later tables added to the ORM metadata.
    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[Base.metadata.tables[name] for name in BASE_TABLES],
        checkfirst=False,
    )


def downgrade() -> None:
    raise RuntimeError("Restaurar backup, sem apagar tabelas com histórico")

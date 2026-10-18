"""SPEC-006B-5.1 — append-only-by-API journal for successful verified reads.

No historical backfill. This migration is never invoked at ordinary startup.
"""
from alembic import op
import sqlalchemy as sa

revision = "006b3_history_access_audit"
down_revision = "006b2_queue_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "history_access_audit",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("user_id", sa.String(40),
                  sa.ForeignKey("auth_users.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("operation_id", sa.String(40), nullable=False),
        sa.Column("queue_id", sa.String(60),
                  sa.ForeignKey("queues.id"), nullable=False),
        sa.Column("session_id", sa.String(40),
                  sa.ForeignKey("handoff_sessions.id"), nullable=True),
        sa.Column("resource", sa.String(16), nullable=False),
        sa.Column("message_page", sa.Integer(), nullable=True),
        sa.Column("event_page", sa.Integer(), nullable=True),
        sa.Column("page_size", sa.Integer(), nullable=False),
        sa.Column("returned_messages", sa.Integer(), nullable=False),
        sa.Column("returned_events", sa.Integer(), nullable=False),
        sa.Column("returned_sessions", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_history_audit_scope_time", "history_access_audit",
        ["operation_id", "queue_id", "created_at"],
    )
    op.create_index(
        "ix_history_audit_user_time", "history_access_audit",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    # Even one audit event is evidence and must not be silently destroyed.
    bind = op.get_bind()
    found = bind.execute(sa.text('SELECT count(*) FROM "history_access_audit"')).scalar_one()
    if found:
        raise RuntimeError("Refusing destructive downgrade: history audit rows exist")
    op.drop_index("ix_history_audit_user_time", table_name="history_access_audit")
    op.drop_index("ix_history_audit_scope_time", table_name="history_access_audit")
    op.drop_table("history_access_audit")

"""SPEC-007/A1.2: offline opt-in lifecycle ledger, zero historical backfill."""
from alembic import op
import sqlalchemy as sa

revision = "007a2_queue_lifecycle"
down_revision = "006b4_security_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "queue_lifecycle",
        sa.Column("queue_id", sa.String(60), sa.ForeignKey("queues.id"),
                  primary_key=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by", sa.String(40),
                  sa.ForeignKey("auth_users.id"), nullable=False),
        sa.CheckConstraint("state IN ('DRAFT','ACTIVE','PAUSED','ARCHIVED')",
                           name="ck_queue_lifecycle_state"),
        sa.CheckConstraint("version >= 1", name="ck_queue_lifecycle_version"),
    )
    op.create_table(
        "queue_lifecycle_events",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("queue_id", sa.String(60), sa.ForeignKey("queues.id"), nullable=False),
        sa.Column("operation_id", sa.String(40), nullable=False),
        sa.Column("actor_user_id", sa.String(40),
                  sa.ForeignKey("auth_users.id"), nullable=False),
        sa.Column("from_state", sa.String(16), nullable=True),
        sa.Column("to_state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lifecycle_events_queue_time", "queue_lifecycle_events",
                    ["queue_id", "created_at"])
    op.create_index("ix_lifecycle_events_operation_time", "queue_lifecycle_events",
                    ["operation_id", "created_at"])


def downgrade() -> None:
    db = op.get_bind()
    for name in ("queue_lifecycle_events", "queue_lifecycle"):
        if db.execute(sa.text('SELECT COUNT(*) FROM "' + name + '"')).scalar_one():
            raise RuntimeError("Lifecycle records exist; refusing destructive downgrade")
    op.drop_index("ix_lifecycle_events_operation_time",
                  table_name="queue_lifecycle_events")
    op.drop_index("ix_lifecycle_events_queue_time",
                  table_name="queue_lifecycle_events")
    op.drop_table("queue_lifecycle_events")
    op.drop_table("queue_lifecycle")

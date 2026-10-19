"""SPEC-006B-5.2: additive security decisions journal without backfill."""
from alembic import op
import sqlalchemy as sa

revision = "006b4_security_decisions"
down_revision = "006b3_history_access_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_decisions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("actor_user_id", sa.String(40),
                  sa.ForeignKey("auth_users.id"), nullable=False),
        sa.Column("actor_role", sa.String(16), nullable=False),
        sa.Column("operation_id", sa.String(40), nullable=False),
        sa.Column("queue_id", sa.String(60),
                  sa.ForeignKey("queues.id"), nullable=True),
        sa.Column("target_user_id", sa.String(40),
                  sa.ForeignKey("auth_users.id"), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_security_decisions_operation_time", "security_decisions",
        ["operation_id", "created_at"],
    )
    op.create_index(
        "ix_security_decisions_actor_time", "security_decisions",
        ["actor_user_id", "created_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text(
        'SELECT count(*) FROM "security_decisions"'
    )).scalar_one():
        raise RuntimeError("Refusing destructive downgrade: security decisions exist")
    op.drop_index("ix_security_decisions_actor_time", table_name="security_decisions")
    op.drop_index("ix_security_decisions_operation_time", table_name="security_decisions")
    op.drop_table("security_decisions")

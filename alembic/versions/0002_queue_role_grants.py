"""Queue-scoped roles are distinct from dispatch memberships."""
import sqlalchemy as sa
from alembic import op

revision = "0002_queue_grants"
down_revision = "0001_poc_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "queue_role_grants",
        sa.Column("user_id", sa.String(40), sa.ForeignKey("auth_users.id"),
                  primary_key=True, nullable=False),
        sa.Column("queue_id", sa.String(60), sa.ForeignKey("queues.id"),
                  primary_key=True, nullable=False),
        sa.Column("role", sa.String(24), primary_key=True, nullable=False),
        sa.Column("granted_by", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_queue_role_grants_queue_role",
        "queue_role_grants", ["queue_id", "role"],
    )


def downgrade() -> None:
    raise RuntimeError("Revogar concessões explicitamente; não remover tabela de segurança")

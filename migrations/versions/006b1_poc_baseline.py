"""SPEC-006B-1: exact POC schema baseline for new databases only.

Existing databases must be inspected, backed up, and adopted using schema_admin.
This revision intentionally refuses to run against a nonempty legacy schema.
"""
from alembic import op
from sqlalchemy import inspect

revision = "006b1_poc_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names()) - {"alembic_version"}
    if existing:
        raise RuntimeError(
            "Nonempty SQLite schema detected. Use schema_admin inspect and adopt "
            "after a verified backup, not 'alembic upgrade head'."
        )
    from handoff_hub.poc_db import Base

    # The baseline is a snapshot of the entire POC-006A schema. Future schema
    # modifications MUST use additive version-specific Alembic operations.
    Base.metadata.create_all(bind=bind, checkfirst=False)


def downgrade() -> None:
    raise RuntimeError("Cannot downgrade the baseline without destroying data")

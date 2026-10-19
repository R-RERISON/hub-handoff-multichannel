"""SPEC-006B-2: additive, empty queue-segment provenance tables.

NO backfill and NO changes to the already-recorded messages or transfers.
Legacy content remains inaccessible to scoped readers until verified mapping
and authorization are implemented in 006B-3/4.
"""
from alembic import op
import sqlalchemy as sa

revision = "006b2_queue_provenance"
down_revision = "006b1_poc_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_queue_segments",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("session_id", sa.String(40),
                  sa.ForeignKey("handoff_sessions.id"), nullable=False),
        sa.Column("queue_id", sa.String(60), sa.ForeignKey("queues.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transfer_id", sa.String(40),
                  sa.ForeignKey("session_transfers.id"), nullable=True),
        sa.Column("provenance_state", sa.String(16), nullable=False),
        sa.UniqueConstraint("session_id", "ordinal",
                            name="uq_session_queue_segment_order"),
    )
    op.create_index("ix_segments_queue_started",
                    "session_queue_segments", ["queue_id", "started_at"])
    op.create_index("ix_segments_session_order",
                    "session_queue_segments", ["session_id", "ordinal"])
    op.create_table(
        "message_queue_provenance",
        sa.Column("message_id", sa.String(40),
                  sa.ForeignKey("messages.id"), primary_key=True),
        sa.Column("segment_id", sa.String(40),
                  sa.ForeignKey("session_queue_segments.id"), nullable=True),
        sa.Column("assigned_by", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
    )
    op.create_index("ix_message_provenance_segment",
                    "message_queue_provenance", ["segment_id"])
    op.create_table(
        "session_event_queue_provenance",
        sa.Column("event_id", sa.String(40),
                  sa.ForeignKey("session_events.id"), primary_key=True),
        sa.Column("segment_id", sa.String(40),
                  sa.ForeignKey("session_queue_segments.id"), nullable=True),
        sa.Column("assigned_by", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
    )
    op.create_index("ix_event_provenance_segment",
                    "session_event_queue_provenance", ["segment_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "session_event_queue_provenance",
        "message_queue_provenance",
        "session_queue_segments",
    ):
        if bind.execute(sa.text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one():
            raise RuntimeError("Refusing destructive downgrade: provenance rows exist")
    op.drop_index("ix_event_provenance_segment",
                  table_name="session_event_queue_provenance")
    op.drop_table("session_event_queue_provenance")
    op.drop_index("ix_message_provenance_segment",
                  table_name="message_queue_provenance")
    op.drop_table("message_queue_provenance")
    op.drop_index("ix_segments_session_order",
                  table_name="session_queue_segments")
    op.drop_index("ix_segments_queue_started",
                  table_name="session_queue_segments")
    op.drop_table("session_queue_segments")

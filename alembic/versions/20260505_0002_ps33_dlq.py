"""PS3.3: DLQ table for telemetry persister retries."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260505_0002"
down_revision = "20260501_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dlq_events",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, nullable=False, autoincrement=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_error", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("last_error_hash", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=True),
        sa.Column("incident_id", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        "ix_dlq_events_created_at", "dlq_events", ["created_at"], unique=False
    )
    op.create_index("ix_dlq_events_event_id", "dlq_events", ["event_id"], unique=False)
    op.create_index(
        "ix_dlq_events_reason_created_at",
        "dlq_events",
        ["reason", "created_at"],
        unique=False,
    )
    op.execute(
        "COMMENT ON TABLE dlq_events IS 'PS3.3 dead-letter queue rows for failed telemetry processing.';"
    )


def downgrade() -> None:
    op.drop_index("ix_dlq_events_reason_created_at", table_name="dlq_events")
    op.drop_index("ix_dlq_events_event_id", table_name="dlq_events")
    op.drop_index("ix_dlq_events_created_at", table_name="dlq_events")
    op.drop_table("dlq_events")

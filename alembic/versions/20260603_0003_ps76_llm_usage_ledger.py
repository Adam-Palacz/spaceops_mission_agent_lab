"""PS7.6: shared daily LLM token ledger for postgres budget mode."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260603_0003"
down_revision = "20260505_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_ledger",
        sa.Column("usage_date", sa.Date(), primary_key=True, nullable=False),
        sa.Column(
            "tokens_used",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        "COMMENT ON TABLE llm_usage_ledger IS "
        "'PS7.6 UTC-day token totals for LLM_BUDGET_MODE=postgres shared org cap.';"
    )


def downgrade() -> None:
    op.drop_table("llm_usage_ledger")

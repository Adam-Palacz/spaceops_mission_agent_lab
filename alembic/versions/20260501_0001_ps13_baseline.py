"""PS1.3 baseline schema: telemetry/incidents/runs/audit."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260501_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "telemetry_events",
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column(
            "schema_version", sa.Text(), nullable=False, server_default=sa.text("'v1'")
        ),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_telemetry_events_ts", "telemetry_events", ["ts"], unique=False)
    op.create_index(
        "ix_telemetry_events_channel_ts",
        "telemetry_events",
        ["channel", "ts"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_telemetry_schema_version_v1",
        "telemetry_events",
        "schema_version = 'v1'",
    )

    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column(
            "schema_version", sa.Text(), nullable=False, server_default=sa.text("'v1'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'open'")
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("incident_id"),
    )
    op.create_check_constraint(
        "ck_incidents_schema_version_v1",
        "incidents",
        "schema_version = 'v1'",
    )
    op.create_index(
        "ix_incidents_created_at", "incidents", ["created_at"], unique=False
    )

    op.create_table(
        "runs",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "llm_calls_used", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.incident_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        "ix_runs_incident_id_started_at",
        "runs",
        ["incident_id", "started_at"],
        unique=False,
    )
    op.create_index("ix_runs_started_at", "runs", ["started_at"], unique=False)

    op.create_table(
        "audit_log",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, nullable=False, autoincrement=True
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("tool", sa.Text(), nullable=False),
        sa.Column("args_hash", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("policy_result", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        "ix_audit_log_incident_id_timestamp",
        "audit_log",
        ["incident_id", "timestamp"],
        unique=False,
    )
    op.create_index("ix_audit_log_trace_id", "audit_log", ["trace_id"], unique=False)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_mutation_append_only()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'append-only table: % is immutable', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_telemetry_events_no_update
        BEFORE UPDATE OR DELETE ON telemetry_events
        FOR EACH ROW EXECUTE FUNCTION prevent_mutation_append_only();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_log_no_update
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION prevent_mutation_append_only();
        """
    )

    op.execute(
        "COMMENT ON TABLE telemetry_events IS 'TelemetryEventV1 append-only event stream.';"
    )
    op.execute(
        "COMMENT ON COLUMN telemetry_events.event_id IS 'TelemetryEventV1.event_id';"
    )
    op.execute(
        "COMMENT ON COLUMN telemetry_events.ts IS 'TelemetryEventV1.ts (UTC timestamp).';"
    )
    op.execute(
        "COMMENT ON COLUMN telemetry_events.source IS 'TelemetryEventV1.source';"
    )
    op.execute(
        "COMMENT ON COLUMN telemetry_events.channel IS 'TelemetryEventV1.channel';"
    )
    op.execute("COMMENT ON COLUMN telemetry_events.value IS 'TelemetryEventV1.value';")
    op.execute("COMMENT ON COLUMN telemetry_events.unit IS 'TelemetryEventV1.unit';")
    op.execute(
        "COMMENT ON COLUMN telemetry_events.payload IS 'Raw source payload snapshot for debugging.';"
    )

    op.execute(
        "COMMENT ON TABLE incidents IS 'IncidentV1 records and lifecycle status.';"
    )
    op.execute("COMMENT ON COLUMN incidents.incident_id IS 'IncidentV1.incident_id';")
    op.execute("COMMENT ON COLUMN incidents.payload IS 'IncidentV1 payload JSON.';")

    op.execute("COMMENT ON TABLE runs IS 'Execution metadata for each agent run.';")
    op.execute(
        "COMMENT ON COLUMN runs.run_id IS 'Stable run identifier (UUID/trace-correlated).';"
    )
    op.execute(
        "COMMENT ON COLUMN runs.metadata IS 'Replay and observability metadata.';"
    )

    op.execute(
        "COMMENT ON TABLE audit_log IS 'Append-only audit trail for human and agent decisions.';"
    )
    op.execute(
        "COMMENT ON COLUMN audit_log.args_hash IS 'Hash of action arguments as in audit schema.';"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_no_update ON audit_log;")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_telemetry_events_no_update ON telemetry_events;"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_mutation_append_only();")

    op.drop_index("ix_audit_log_trace_id", table_name="audit_log")
    op.drop_index("ix_audit_log_incident_id_timestamp", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_runs_started_at", table_name="runs")
    op.drop_index("ix_runs_incident_id_started_at", table_name="runs")
    op.drop_table("runs")

    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_constraint("ck_incidents_schema_version_v1", "incidents", type_="check")
    op.drop_table("incidents")

    op.drop_constraint(
        "ck_telemetry_schema_version_v1", "telemetry_events", type_="check"
    )
    op.drop_index("ix_telemetry_events_channel_ts", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_ts", table_name="telemetry_events")
    op.drop_table("telemetry_events")

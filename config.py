"""
SpaceOps Mission Agent Lab — central config from environment.
Loads .env from repo root so secrets stay out of shell history and are never committed.
Use: from config import settings
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(_REPO_ROOT / ".env", override=False)


class Settings(BaseSettings):
    """Environment-based settings. Prefer env vars over .env file (override=False above)."""

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI (KB embedding + agent)
    openai_api_key: str = Field(
        default="", description="OpenAI API key; required for KB and agent."
    )

    # Postgres (RAG, KB)
    database_url: str = Field(
        default="", description="Full DB URL; overrides POSTGRES_* if set."
    )
    postgres_host: str = Field(default="localhost")
    postgres_port: str = Field(default="5432")
    postgres_user: str = Field(default="spaceops")
    # Optional for core app (API/agent without KB); required when using KB server or indexer.
    postgres_password: str = Field(
        default="",
        description="Postgres password; required for KB/RAG, optional otherwise.",
    )
    postgres_db: str = Field(default="spaceops")

    # MCP servers (agent calls these in S1.7, S2.2)
    telemetry_mcp_url: str = Field(default="http://localhost:8001/mcp")
    kb_mcp_url: str = Field(default="http://localhost:8002/mcp")
    ticket_mcp_url: str = Field(
        default="http://localhost:8003/mcp",
        description="MCP Ticketing (create_ticket); S2.2.",
    )
    gitops_mcp_url: str = Field(
        default="http://localhost:8004/mcp",
        description="MCP GitOps (create_pr to ops-config); S2.2.",
    )

    # OPA (S2.4): policy for restricted actions (Act node).
    opa_url: str = Field(
        default="http://localhost:8181/v1/data/agent/allow",
        description="OPA policy endpoint for restricted actions (POST with {input:{incident_id,step}}).",
    )
    opa_timeout_seconds: int = Field(
        default=2,
        description="OPA HTTP timeout (seconds). On timeout/error → deny (fail-closed, NF8).",
    )

    # GitOps: push branch + create PR (S2.2). Empty = only write files locally.
    github_token: str = Field(
        default="",
        description="GitHub token (repo scope) for push and Create PR; empty = no push/PR.",
    )
    github_repo: str = Field(
        default="",
        description="GitHub repo 'owner/name' for ops-config (or main repo with ops-config subtree); required for push/PR.",
    )
    github_repo_base_branch: str = Field(
        default="main",
        description="Base branch for new PRs (e.g. main).",
    )

    # OTel (S1.10): export traces to Collector; empty = disable tracing
    otel_exporter_otlp_endpoint: str = Field(
        default="",
        description="OTLP gRPC endpoint (e.g. http://localhost:4317); empty = no export",
    )

    # Jaeger (trace link in report)
    jaeger_ui_url: str = Field(default="http://localhost:16686")

    # Audit log (S1.9): path to NDJSON file; empty = use repo data/audit.ndjson
    audit_log_path: str = Field(
        default="",
        description="Path to append-only audit NDJSON; empty = data/audit.ndjson",
    )

    # S2.5 Approval API: storage and auth
    approval_store_path: str = Field(
        default="",
        description="Directory for approval request JSON files; empty = data/approvals",
    )
    approval_api_key: str = Field(
        default="",
        description="API key for approve/reject (header X-API-Key or Authorization: Bearer <key>). Required for POST approve/reject.",
    )

    # S1.12 NF6: token/rate limits and timeouts; on limit or timeout → escalation
    agent_run_timeout_seconds: int = Field(
        default=120, description="Max wall-clock time per run; 0 = no limit"
    )
    agent_llm_call_timeout_seconds: int = Field(
        default=30, description="Timeout per LLM call (seconds)"
    )
    agent_token_budget_per_run: int = Field(
        default=50_000, description="Max total tokens per run; 0 = no limit"
    )
    agent_max_llm_calls_per_run: int = Field(
        default=10, description="Max LLM calls per run; 0 = no limit (rate limit NF6)"
    )

    @property
    def postgres_dsn(self) -> str:
        """Connection string when DATABASE_URL is not set."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()  # type: ignore[call-arg]  # postgres_password from env

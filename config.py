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

# S3.7: secrets management stub — future backends can plug in here
from apps.common.secrets import get_secret

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
        default_factory=lambda: get_secret("OPENAI_API_KEY", ""),
        description="OpenAI API key; required for KB and agent.",
    )
    llm_backend: str = Field(
        default="",
        description=(
            "LLM routing backend: openai | cursor_sh | gpu. "
            "When set, overrides deprecated LLM_PROVIDER."
        ),
    )
    llm_provider: str = Field(
        default="",
        description=(
            "Deprecated: use LLM_BACKEND. Legacy alias for openai | cursor_sh when "
            "llm_backend is unset."
        ),
    )
    gpu_llm_base_url: str = Field(
        default="http://localhost:8005",
        description="NIM/OpenAI-compatible base URL when LLM_BACKEND=gpu.",
    )
    gpu_llm_model_id: str = Field(
        default="",
        description="Default model id for GPU backend when LLM_BACKEND=gpu.",
    )
    gpu_llm_api_key: str = Field(
        default_factory=lambda: get_secret("GPU_LLM_API_KEY", ""),
        description="Optional bearer token for GPU/NIM endpoint.",
    )
    llm_openai_cost_per_1k_tokens: float = Field(
        default=0.0,
        description=(
            "Optional USD rate per 1k tokens for OpenAI backend cost estimates (PS5.2); "
            "0 disables estimated_cost_usd."
        ),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com",
        description="OpenAI API base URL (root or full chat completions URL).",
    )
    cursor_sh_api_key: str = Field(
        default_factory=lambda: get_secret("CURSOR_SH_API_KEY", ""),
        description="Cursor.sh API key for agent chat completions when LLM_BACKEND='cursor_sh'.",
    )
    cursor_sh_base_url: str = Field(
        default="https://api.cursor.sh",
        description="Cursor.sh API base URL (root or full chat completions URL).",
    )
    llm_chat_completions_path: str = Field(
        default="/v1/chat/completions",
        description="Path appended to provider base URL when base URL is not already a full endpoint.",
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
        default_factory=lambda: get_secret("POSTGRES_PASSWORD", ""),
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
        default_factory=lambda: get_secret("GITHUB_TOKEN", ""),
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
        default_factory=lambda: get_secret("APPROVAL_API_KEY", ""),
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
    agent_durable_checkpoint_enabled: bool = Field(
        default=False,
        description="Enable Postgres-backed durable checkpoints for LangGraph-like pipeline state.",
    )
    agent_durable_checkpoint_thread_prefix: str = Field(
        default="incident",
        description="Prefix strategy for durable checkpoint thread_id: '<prefix>:<incident_id>'.",
    )

    # S3.1: model lifecycle / shadow-testing
    agent_model_id: str = Field(
        default="gpt-4o-mini",
        description="Current production model identifier for agent triage/decide/report.",
    )
    agent_candidate_model_ids: str = Field(
        default="",
        description="Comma-separated candidate model identifiers for shadow-testing.",
    )

    # S3.3: context window & history compaction
    agent_max_hypotheses: int = Field(
        default=32,
        description="Max number of hypotheses to keep in agent state; 0 = no compaction.",
    )
    agent_max_citations: int = Field(
        default=128,
        description="Max number of citations to keep in agent state; 0 = no compaction.",
    )
    agent_history_compaction_debug: bool = Field(
        default=False,
        description="When true, log when context history is compacted and by how much.",
    )

    # S3.4: HTTP/MCP retry and circuit breaker
    http_resilience_max_retries: int = Field(
        default=3,
        description="Max retries for transient HTTP/MCP failures (0 = no retries).",
    )
    http_resilience_backoff_base_seconds: float = Field(
        default=1.0,
        description="Base delay for exponential backoff between retries.",
    )
    http_resilience_circuit_breaker_failures: int = Field(
        default=5,
        description="Failures before opening circuit (0 = disable circuit breaker).",
    )
    http_resilience_circuit_breaker_reset_seconds: float = Field(
        default=60.0,
        description="Seconds before circuit moves from open to half-open.",
    )

    # P4.4 / NF5: Reranker for KB RAG citation quality
    kb_reranker_enabled: bool = Field(
        default=False,
        description="Enable reranking of retrieved KB chunks (lexical or llm).",
    )
    kb_reranker_mode: str = Field(
        default="lexical",
        description="Reranker mode: 'lexical' (dependency-free) or 'llm' (OpenAI scoring).",
    )
    kb_reranker_retrieve_k: int = Field(
        default=10,
        description="Candidate pool size to rerank in KB search (returned list is still top-N = tool limit).",
    )
    kb_reranker_llm_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model used for LLM reranking (only when kb_reranker_mode='llm').",
    )

    # PS3.2 / ADR 0002 — NATS JetStream ingest (telemetry); empty = legacy NDJSON files
    nats_url: str = Field(
        default="",
        description="NATS server URLs (comma-separated optional); empty disables JetStream ingest.",
    )
    jetstream_stream_name: str = Field(
        default="SPACEOPS_INGEST",
        description="JetStream stream name for ingest workload.",
    )
    jetstream_telemetry_subject: str = Field(
        default="ingest.telemetry",
        description="Subject for validated TelemetryEventV1 JSON payloads.",
    )
    jetstream_persister_durable: str = Field(
        default="telemetry-persister",
        description="Durable consumer name writing telemetry_events (Postgres).",
    )
    jetstream_persister_max_retries: int = Field(
        default=3,
        description="Max delivery attempts before telemetry message goes to DLQ.",
    )
    jetstream_persister_retry_base_seconds: float = Field(
        default=2.0,
        description="Base retry delay (seconds) for telemetry persister NAK backoff.",
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

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
    openai_api_key: str = Field(default="", description="OpenAI API key; required for KB and agent.")

    # Postgres (RAG, KB)
    database_url: str = Field(default="", description="Full DB URL; overrides POSTGRES_* if set.")
    postgres_host: str = Field(default="localhost")
    postgres_port: str = Field(default="5432")
    postgres_user: str = Field(default="spaceops")
    postgres_password: str = Field()
    postgres_db: str = Field(default="spaceops")

    # MCP servers (agent calls these in S1.7)
    telemetry_mcp_url: str = Field(default="http://localhost:8001/mcp")
    kb_mcp_url: str = Field(default="http://localhost:8002/mcp")

    # Jaeger (trace link in report)
    jaeger_ui_url: str = Field(default="http://localhost:16686")

    @property
    def postgres_dsn(self) -> str:
        """Connection string when DATABASE_URL is not set."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()

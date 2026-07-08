"""Runtime configuration.

All secrets come from the environment (or a local .env file); nothing is
hard-coded. Model routing is the token-efficiency lever: the orchestrator is
the ONLY component allowed to use the high-reasoning tier.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelTier(StrEnum):
    """Cost tier a component is allowed to run on. Enforced by the LLM factory."""

    LOW = "low"        # bulk execution: parsing, extraction, formatting
    MEDIUM = "medium"  # structured reasoning: process mining, NLP mapping
    HIGH = "high"      # orchestrator only: synthesis, delegation, evaluation


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LSS_", extra="ignore")

    # --- LLM routing (orchestrator = HIGH, everything else LOW/MEDIUM) ---
    anthropic_api_key: str = Field(default="", repr=False)
    model_low: str = "claude-haiku-4-5-20251001"
    model_medium: str = "claude-sonnet-5"
    model_high: str = "claude-opus-4-8"
    max_tokens_low: int = 2048
    max_tokens_medium: int = 4096
    max_tokens_high: int = 8192

    # --- Connectors ---
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = Field(default="", repr=False)
    sql_dsn: str = ""  # any SQLAlchemy DSN, e.g. postgresql+psycopg://...
    salesforce_instance_url: str = ""
    salesforce_access_token: str = Field(default="", repr=False)
    hubspot_access_token: str = Field(default="", repr=False)

    # --- Sandbox limits for the Statistical Engine ---
    sandbox_timeout_seconds: int = 30
    sandbox_memory_mb: int = 512

    # --- Control phase ---
    spc_poll_interval_seconds: int = 300

    # --- Dashboard sinks ---
    powerbi_push_url: str = Field(default="", repr=False)  # streaming dataset "Push URL"

    def model_for(self, tier: ModelTier) -> str:
        return {
            ModelTier.LOW: self.model_low,
            ModelTier.MEDIUM: self.model_medium,
            ModelTier.HIGH: self.model_high,
        }[tier]

    def max_tokens_for(self, tier: ModelTier) -> int:
        return {
            ModelTier.LOW: self.max_tokens_low,
            ModelTier.MEDIUM: self.max_tokens_medium,
            ModelTier.HIGH: self.max_tokens_high,
        }[tier]


settings = Settings()

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Lead Generation & Outreach Platform"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    database_url: str = Field(alias="DATABASE_URL")

    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_publishable_key: str = Field(
        alias="SUPABASE_PUBLISHABLE_KEY"
    )

    allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="ALLOWED_ORIGINS",
    )

    log_level: str = "INFO"

    cloudflare_account_id: str = Field(
        alias="CLOUDFLARE_ACCOUNT_ID"
    )

    cloudflare_api_token: str = Field(
        alias="CLOUDFLARE_API_TOKEN"
    )

    cloudflare_ai_model: str = Field(
        default="@cf/zai-org/glm-4.7-flash",
        alias="CLOUDFLARE_AI_MODEL",
    )

    email_credential_encryption_key: str = Field(
        alias="EMAIL_CREDENTIAL_ENCRYPTION_KEY"
    )

    # ---------------------------------------------------------
    # Google OAuth
    # ---------------------------------------------------------

    google_client_id: str = Field(
        alias="GOOGLE_CLIENT_ID"
    )

    google_client_secret: str = Field(
        alias="GOOGLE_CLIENT_SECRET"
    )

    google_redirect_uri: str = Field(
        default=(
            "http://127.0.0.1:8000/"
            "api/v1/email-accounts/google/callback"
        ),
        alias="GOOGLE_REDIRECT_URI",
    )

    frontend_url: str = Field(
        default="http://localhost:5173",
        alias="FRONTEND_URL",
    )

    # ---------------------------------------------------------
    # Redis
    # ---------------------------------------------------------

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )

    redis_stream_name: str = Field(
        default="ai-lead-generation:jobs",
        alias="REDIS_STREAM_NAME",
    )

    redis_consumer_group: str = Field(
        default="ai-lead-generation-workers",
        alias="REDIS_CONSUMER_GROUP",
    )

    redis_consumer_name: str = Field(
        default="worker-1",
        alias="REDIS_CONSUMER_NAME",
    )

    worker_poll_interval: int = Field(
        default=5,
        alias="WORKER_POLL_INTERVAL",
        ge=1,
    )

    worker_block_ms: int = Field(
        default=5000,
        alias="WORKER_BLOCK_MS",
        ge=100,
    )

    worker_batch_size: int = Field(
        default=10,
        alias="WORKER_BATCH_SIZE",
        ge=1,
        le=100,
    )

    # ---------------------------------------------------------
    # Scheduler
    # ---------------------------------------------------------

    scheduler_interval_seconds: int = Field(
        default=30,
        alias="SCHEDULER_INTERVAL_SECONDS",
        ge=5,
    )

    scheduler_batch_size: int = Field(
        default=20,
        alias="SCHEDULER_BATCH_SIZE",
        ge=1,
        le=100,
    )

    scheduler_lock_timeout_seconds: int = Field(
        default=120,
        alias="SCHEDULER_LOCK_TIMEOUT_SECONDS",
        ge=30,
    )

    # ---------------------------------------------------------
    # Retry / Failure Recovery
    # ---------------------------------------------------------

    retry_base_delay_seconds: int = Field(
        default=300,
        alias="RETRY_BASE_DELAY_SECONDS",
        ge=1,
    )

    retry_max_delay_seconds: int = Field(
        default=1800,
        alias="RETRY_MAX_DELAY_SECONDS",
        ge=1,
    )

    retry_jitter_seconds: int = Field(
        default=30,
        alias="RETRY_JITTER_SECONDS",
        ge=0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
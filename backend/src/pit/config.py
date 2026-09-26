from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AI_PROVIDERS = {"gemini", "groq", "openai", "azure"}


def _split(value: str) -> list[str]:
    return [part.strip().lower() for part in value.split(",") if part.strip()]


class Settings(BaseSettings):
    """All configuration comes from environment variables prefixed with PIT_ (see .env.example)."""

    model_config = SettingsConfigDict(env_prefix="PIT_", env_file=".env", extra="ignore")

    env: str = "local"
    database_url: str = "postgresql+psycopg://pit:pit@localhost:5433/pit"
    redis_url: str = "redis://localhost:6380/0"
    daily_code_secret: SecretStr  # no default: a guessable secret would make daily codes guessable
    s3_endpoint_url: str = "http://localhost:9100"
    s3_bucket: str = "proofs"
    s3_access_key: str = "pit"
    s3_secret_key: SecretStr = SecretStr("pit-secret-key")
    # local: files on disk served by the API (development); s3: any S3-compatible store.
    storage: Literal["local", "s3", "memory"] = "local"
    local_storage_dir: str = ".storage"
    public_base_url: str = "http://localhost:8000"

    jwt_secret: SecretStr  # no default, same reason
    jwt_ttl_hours: int = 24 * 7

    # AI providers in turn order, e.g. "gemini,groq". They take turns and cover for each other
    # when one is busy or rate-limited. Empty = no AI ("dev"): proofs are auto-approved and
    # plans come from templates — never in production.
    ai_providers: str = ""
    gemini_api_key: SecretStr = SecretStr("")  # aistudio.google.com (has a free tier)
    # *_model checks proof photos (must understand images); *_plan_model writes plans
    # (text only; empty = the same model).
    gemini_model: str = "gemini-3.7-flash"
    gemini_plan_model: str = ""
    groq_api_key: SecretStr = SecretStr("")  # console.groq.com (has a free tier)
    groq_model: str = "qwen/qwen3.8-27b"
    groq_plan_model: str = "openai/gpt-oss-120b"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    openai_plan_model: str = ""
    openai_base_url: str | None = None  # any other OpenAI-compatible service
    azure_api_key: SecretStr = SecretStr("")
    azure_endpoint: str | None = None
    azure_api_version: str = "2024-10-21"
    azure_deployment: str = ""

    # Local development: verify proofs and run daily jobs inside the API process (no Celery).
    inline_tasks: bool = True

    # SMS: "console" logs codes (development); "eskiz" sends real SMS via eskiz.uz.
    sms_provider: Literal["console", "eskiz"] = "console"
    eskiz_email: str = ""
    eskiz_password: SecretStr = SecretStr("")
    eskiz_sender: str = "4546"

    # Telegram bot from @BotFather; an empty token means no bot. Production receives updates
    # on a webhook ({public_base_url}/api/v1/telegram/webhook); "polling" needs no public URL.
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_bot_username: str = ""  # without "@", for t.me links
    telegram_webhook_secret: SecretStr = SecretStr("")
    telegram_mode: Literal["webhook", "polling"] = "webhook"
    # "Sign in with Google": the OAuth Web client id from Google Cloud Console; empty = off.
    google_client_id: str = ""

    # The website, for links in bot messages (production: same domain as public_base_url).
    web_url: str = "http://localhost:3100"

    # Paid features (stake mode, wallet). Off: the whole platform is free.
    stakes_enabled: bool = False

    # Browser push notifications (Web Push / VAPID). Generate: `python -m pit.cli vapid-keys`.
    vapid_public_key: str = ""
    vapid_private_key: SecretStr = SecretStr("")
    vapid_subject: str = "mailto:support@pit.uz"

    # Error tracking (sentry.io); empty = off.
    sentry_dsn: SecretStr = SecretStr("")
    sentry_traces_sample_rate: float = 0.1

    rate_limits_enabled: bool = True
    # Only behind a trusted reverse proxy (Caddy in docker-compose.prod.yml).
    trust_proxy_headers: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_local(self) -> bool:
        return self.env == "local"

    @field_validator("ai_providers")
    @classmethod
    def _known_providers(cls, value: str) -> str:
        unknown = set(_split(value)) - AI_PROVIDERS
        if unknown:
            raise ValueError(f"Unknown AI providers: {', '.join(sorted(unknown))}")
        return value

    @property
    def ai_provider_names(self) -> list[str]:
        return _split(self.ai_providers)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token.get_secret_value() and self.telegram_bot_username)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # required fields come from the environment

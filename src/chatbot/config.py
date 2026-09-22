# src/chatbot/config.py

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "chatbot"
    environment: str = "development"
    debug: bool = False

    # API
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/chatbot"
    )

    # AI
    ai_model: str = "openai:gpt-4.1-mini"
    ai_temperature: float = Field(
        default=0.2,
        ge=0,
        le=2,
    )
    ai_max_tokens: int | None = None
    ai_timeout: float = 30.0
    ai_max_retries: int = Field(
        default=3,
        ge=0,
    )

    # Provider credentials
    openai_api_key: str | None = None

    # Security
    jwt_secret: str = Field(
        default="development-only-secret-change-in-production",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

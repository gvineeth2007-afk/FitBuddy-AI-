from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitBuddy"
    database_url: str = "sqlite:///./fitbuddy.db"

    gemini_api_key: str | None = None
    gemini_workout_model: str = "gemini-2.5-pro"
    gemini_fast_model: str = "gemini-2.5-flash"

    admin_key: str = "change-me"
    mock_ai: bool = False
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

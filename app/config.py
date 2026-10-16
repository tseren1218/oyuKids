from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OYU_", extra="ignore")

    app_name: str = "oyuKids"
    debug: bool = True
    session_secret: str = "dev-only-change-me"

    db_backend: Literal["memory", "singlestore"] = "memory"
    singlestore_url: str | None = None

    stt_provider: Literal["mock", "oyu"] = "mock"
    stt_api_key: str | None = None
    stt_model: str | None = None  # e.g. "v4"; omitted → oyu's default
    oyu_api_url: str = "https://api.oyu.so"


@lru_cache
def get_settings() -> Settings:
    return Settings()

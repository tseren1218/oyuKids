from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OYU_", extra="ignore")

    app_name: str = "oyuKids"
    debug: bool = True

    db_backend: Literal["memory", "singlestore"] = "memory"
    singlestore_url: str | None = None

    stt_provider: Literal["mock", "http"] = "mock"
    stt_api_url: str | None = None
    stt_api_key: str | None = None
    stt_language: str = "mn-MN"


@lru_cache
def get_settings() -> Settings:
    return Settings()

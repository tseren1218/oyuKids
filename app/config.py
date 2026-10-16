from functools import lru_cache
from typing import Literal

from pydantic import Field
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

    # Recordings → S3 (standard AWS variable names, no OYU_ prefix). Unset → recordings aren't stored.
    aws_access_key_id: str | None = Field(None, validation_alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(None, validation_alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("ap-southeast-1", validation_alias="AWS_REGION")
    s3_bucket_name: str | None = Field(None, validation_alias="S3_BUCKET_NAME")


@lru_cache
def get_settings() -> Settings:
    return Settings()

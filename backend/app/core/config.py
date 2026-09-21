from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "高校社团活动管理系统 API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(default="change-me-in-local-env-at-least-32-bytes", min_length=32)
    access_token_expire_minutes: int = 60
    database_url: str = "mysql+pymysql://club_app:club_app@127.0.0.1:3306/club_management?charset=utf8mb4"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    BASE_URL: str = "http://localhost:8000"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    DATABASE_URL: str = "postgresql+asyncpg://botocharcoal:password@localhost:5432/botocharcoal"
    REDIS_URL: str = "redis://localhost:6379/0"

    OPENAI_API_KEY: str = ""
    TEXT_MODEL: str = "gpt-4o"
    IMAGE_MODEL: str = "dall-e-3"

    GRAPH_API_VERSION: str = "v20.0"
    IG_LONG_LIVED_ACCESS_TOKEN: str = ""
    IG_BUSINESS_ACCOUNT_ID: str = ""

    MEDIA_ROOT: str = "media"
    MEDIA_URL: str = "/media/"

    ADMIN_SESSION_MAX_AGE: int = 86400
    CELERY_MAX_RETRIES: int = 3

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

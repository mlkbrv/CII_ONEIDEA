from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cci:postgres@127.0.0.1:5432/cci"
    promo_code_pepper: str = ""
    telegram_bot_token: str = ""
    telegram_webapp_url: str = ""
    telegram_init_data_max_age_seconds: int = 86400
    bot_polling: bool = True
    jwt_secret: str = "change-me-use-a-32-byte-or-longer-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080


@lru_cache
def get_settings() -> Settings:
    return Settings()

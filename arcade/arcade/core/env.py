from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    WORK_DIR: Path = Path.home() / ".arcade"


@lru_cache
def get_settings() -> Settings:
    # env_file = os.getenv("ARCADE_ENV_FILE")
    # TODO allow env override
    return Settings()


settings = get_settings()

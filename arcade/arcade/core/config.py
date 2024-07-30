from pathlib import Path

import toml
from pydantic import BaseModel

from arcade.core.env import settings


class ApiConfig(BaseModel):
    key: str
    secret: str


class UserConfig(BaseModel):
    email: str | None = None


class EngineConfig(BaseModel):
    key: str | None = None
    host: str = "localhost"
    port: str = "6901"
    tls: bool = False


class Config(BaseModel):
    api: ApiConfig
    user: UserConfig | None = None
    engine: EngineConfig | None = None

    @classmethod
    def get_config_dir_path(cls) -> Path:
        return settings.WORK_DIR if settings.WORK_DIR else Path.home() / ".arcade"

    @classmethod
    def get_config_file_path(cls) -> Path:
        return cls.get_config_dir_path() / "arcade.toml"

    @property
    def engine_url(self) -> str:
        if self.engine is None:
            raise ValueError("Engine not set")
        protocol = "https" if self.engine.tls else "http"
        return f"{protocol}://{self.engine.host}:{self.engine.port}"

    @classmethod
    def create_config_directory(cls) -> None:
        """
        Create the configuration directory if it does not exist.
        """
        config_dir = Config.get_config_dir_path()
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_from_file(cls) -> "Config":
        """
        Load the configuration from the TOML file in the configuration directory.
        """
        cls.create_config_directory()

        config_file_path = cls.get_config_file_path()
        if not config_file_path.exists():
            raise ValueError("Config file does not exist")

        config_data = toml.loads(config_file_path.read_text())
        return cls(**config_data)

    def save_to_file(self) -> None:
        """
        Save the configuration to the TOML file in the configuration directory.
        """
        Config.create_config_directory()
        config_file_path = Config.get_config_file_path()
        config_file_path.write_text(toml.dumps(self.model_dump()))


# Singleton instance of Config
config = Config.load_from_file()

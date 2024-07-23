from pathlib import Path

import toml
from pydantic import BaseModel

from arcade.core.env import settings


class Config(BaseModel):
    api_key: str | None = None
    user_email: str | None = None
    engine_key: str | None = None
    engine_host: str = "localhost"
    engine_port: str = "6901"

    config_dir: Path = settings.WORK_DIR if settings.WORK_DIR else Path.home() / ".arcade"
    config_file: Path = config_dir / "arcade.toml"

    @property
    def arcade_api_key(self) -> str:
        if not self.api_key:
            raise ValueError("Arcade API Key not set")
        return self.api_key

    @property
    def engine_url(self, tls: bool = False) -> str:
        if tls:
            return f"https://{self.engine_host}:{self.engine_port}"
        return f"http://{self.engine_host}:{self.engine_port}"

    @staticmethod
    def create_config_directory() -> None:
        """
        Create the configuration directory if it does not exist.
        """
        config_dir = Config.config_dir
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

    def save_to_file(self) -> None:
        """
        Save the configuration to the TOML file in the configuration directory.
        """
        self.create_config_directory()
        config_file_path = self.config_file
        with config_file_path.open("w") as config_file:
            toml.dump(self.dict(), config_file)

    @classmethod
    def load_from_file(cls) -> "Config":
        """
        Load the configuration from the TOML file in the configuration directory.
        """
        cls.create_config_directory()
        config_file_path = cls.config_file
        if config_file_path.exists():
            with config_file_path.open("r") as config_file:
                config_data = toml.load(config_file)
                return cls(**config_data)
        return cls()


# Singleton instance of Config
config = Config.load_from_file()

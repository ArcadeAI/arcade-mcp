from pathlib import Path

import toml
from pydantic import BaseModel, ValidationError

from arcade.core.env import settings


class ApiConfig(BaseModel):
    """
    Arcade API configuration.
    """

    key: str
    """
    Arcade API key.
    """


class UserConfig(BaseModel):
    """
    Arcade user configuration.
    """

    email: str | None = None
    """
    User email.
    """


class EngineConfig(BaseModel):
    """
    Arcade Engine configuration.
    """

    host: str = "localhost"
    """
    Arcade Engine host.
    """
    port: int = 6901
    """
    Arcade Engine port.
    """
    tls: bool = False
    """
    Whether to use TLS for the connection to Arcade Engine.
    """


class Config(BaseModel):
    """
    Configuration for Arcade.
    """

    api: ApiConfig
    """
    Arcade API configuration.
    """
    user: UserConfig | None = None
    """
    Arcade user configuration.
    """
    engine: EngineConfig | None = None
    """
    Arcade Engine configuration.
    """

    @classmethod
    def get_config_dir_path(cls) -> Path:
        """
        Get the path to the Arcade configuration directory.
        """
        return settings.WORK_DIR if settings.WORK_DIR else Path.home() / ".arcade"

    @classmethod
    def get_config_file_path(cls) -> Path:
        """
        Get the path to the Arcade configuration file.
        """
        return cls.get_config_dir_path() / "arcade.toml"

    @property
    def engine_url(self) -> str:
        """
        Get the URL of the Arcade Engine.
        """
        if self.engine is None:
            raise ValueError("Engine not set")
        protocol = "https" if self.engine.tls else "http"
        return f"{protocol}://{self.engine.host}:{self.engine.port}/v1"

    @classmethod
    def ensure_config_dir_exists(cls) -> None:
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
        If no configuration file exists, create a new one with default values.
        """
        cls.ensure_config_dir_exists()

        config_file_path = cls.get_config_file_path()
        if not config_file_path.exists():
            # Create a file using the default configuration
            default_config = cls.model_construct(
                api=ApiConfig.model_construct(), engine=EngineConfig()
            )
            default_config.save_to_file()

        config_data = toml.loads(config_file_path.read_text())

        try:
            return cls(**config_data)
        except ValidationError as e:
            # Get only the errors with {type:missing} and combine them
            # into a nicely-formatted string message.
            # Any other errors without {type:missing} should just be str()ed
            missing_field_errors = [
                ".".join(map(str, error["loc"]))
                for error in e.errors()
                if error["type"] == "missing"
            ]
            other_errors = [str(error) for error in e.errors() if error["type"] != "missing"]

            missing_field_errors_str = ", ".join(missing_field_errors)
            other_errors_str = "\n".join(other_errors)

            pretty_str: str = "Invalid Arcade configuration."
            if missing_field_errors_str:
                pretty_str += f"\nMissing fields: {missing_field_errors_str}\n"
            if other_errors_str:
                pretty_str += f"\nOther errors:\n{other_errors_str}"

            raise ValueError(pretty_str) from e

    def save_to_file(self) -> None:
        """
        Save the configuration to the TOML file in the configuration directory.
        """
        Config.ensure_config_dir_exists()
        config_file_path = Config.get_config_file_path()
        config_file_path.write_text(toml.dumps(self.model_dump()))


# Singleton instance of Config
config = Config.load_from_file()

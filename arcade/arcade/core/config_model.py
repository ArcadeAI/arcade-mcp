import os
from pathlib import Path
from typing import Any

import toml
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError


class BaseConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ApiConfig(BaseConfig):
    """
    Arcade API configuration.
    """

    key: str
    """
    Arcade API key.
    """
    version: str = "v1"
    """
    Arcade API version.
    """


class UserConfig(BaseConfig):
    """
    Arcade user configuration.
    """

    email: str | None = None
    """
    User email.
    """


class Config(BaseConfig):
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

    def __init__(self, **data: Any):
        super().__init__(**data)

    @classmethod
    def get_config_dir_path(cls) -> Path:
        """
        Get the path to the Arcade configuration directory.
        """
        config_path = os.getenv("ARCADE_WORK_DIR") or Path.home() / ".arcade"
        return Path(config_path).resolve()

    @classmethod
    def get_deprecated_config_file_path(cls) -> Path:
        """
        Get the path to the deprecated Arcade configuration file.
        """
        return cls.get_config_dir_path() / "arcade.toml"

    @classmethod
    def get_config_file_path(cls) -> Path:
        """
        Get the path to the Arcade configuration file.
        """
        return cls.get_config_dir_path() / "credentials.yaml"

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
        Load the configuration from the YAML file in the configuration directory.

        If no configuration file exists, this method will create a new one with default values.
        The default configuration includes:
        - An empty API configuration
        - A default Engine configuration (host: "api.arcade-ai.com", port: None, tls: True)
        - No user configuration

        If a deprecated TOML configuration file is found, it will be automatically converted
        to the new YAML format. This ensures that the application always has a valid configuration
        to work with, but it may not be suitable for all use cases. If a specific configuration
        is required, ensure that the configuration file exists before calling this method.

        Returns:
            Config: The loaded or newly created configuration.

        Raises:
            ValueError: If the existing configuration file is invalid or cannot be converted.
        """
        cls.ensure_config_dir_exists()

        config_file_path = cls.get_config_file_path()

        if not config_file_path.exists() and not cls._migrate_deprecated_config_file():
            # Create a file using the default configuration
            default_config = cls.model_construct(api=ApiConfig.model_construct())
            default_config.save_to_file()

        config_data = yaml.safe_load(config_file_path.read_text())

        try:
            return cls(**config_data["cloud"])
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
        Save the configuration to the YAML file in the configuration directory.
        """
        Config.ensure_config_dir_exists()
        config_file_path = Config.get_config_file_path()
        config_file_path.write_text(yaml.dump(self.model_dump()))

    @classmethod
    def _migrate_deprecated_config_file(cls) -> bool:
        """
        Migrate the deprecated config file to the new format if the deprecated config file exists.

        Returns:
            bool: True if the migration occurred, False otherwise.
        """
        deprecated_config_file_path = Config.get_deprecated_config_file_path()

        if deprecated_config_file_path.exists():
            # If the user is using the deprecated config file, then convert it to the new yaml format
            try:
                old_config: dict[str, Any] = toml.load(deprecated_config_file_path)
                old_config = {"cloud": old_config}
                with open(cls.get_config_file_path(), "w") as f:
                    yaml.dump(old_config, f)
                os.remove(deprecated_config_file_path)
                print(
                    f"\033[1;33mAutomatically migrated the deprecated config file {deprecated_config_file_path} to {cls.get_config_file_path()}\033[0m"
                )
            except Exception as e:
                raise OSError(
                    f"Invalid configuration file at {deprecated_config_file_path} could not be automatically converted to the new format. Please manually migrate to {cls.get_config_file_path()} by running `arcade logout && arcade login`."
                ) from e
            return True
        return False

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

CONFIG_VERSION = "2"


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


class ProfileConfig(BaseConfig):
    """
    Arcade profile configuration.
    """

    name: str = "default"
    """
    Profile name.
    """
    api: ApiConfig | None = None
    """
    Profile API configuration.
    """
    user: UserConfig | None = None
    """
    Profile user configuration.
    """


class Config(BaseConfig):
    """
    Configuration for Arcade.
    """

    version: str = CONFIG_VERSION
    """
    Arcade configuration version.
    """
    profiles: dict[str, ProfileConfig] = {}
    """
    Dictionary of profiles.
    """

    def __init__(self, **data: Any) -> None:
        profiles_input = data.get("profiles", {})
        profiles: dict[str, ProfileConfig] = {}
        names_seen: list[str] = []
        for name, config in profiles_input.items():
            if not isinstance(config, ProfileConfig):
                raise TypeError(
                    f"Invalid credentials.yaml file. Profile '{name}' is not a valid ProfileConfig instance."
                )
            if name in names_seen:
                raise ValueError(
                    f"Invalid credentials.yaml file. Profile name '{name}' is not unique."
                )
            names_seen.append(name)
            profiles[name] = config
        data["profiles"] = profiles
        super().__init__(**data)

    @classmethod
    def get_config_dir_path(cls) -> Path:
        """
        Get the path to the Arcade configuration directory.
        """
        config_path = os.getenv("ARCADE_WORK_DIR") or Path.home() / ".arcade"
        return Path(config_path).resolve()

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
        - A default Engine configuration (host: "api.arcade.dev", port: None, tls: True)
        - No user configuration

        Returns:
            Config: The loaded or newly created configuration.

        Raises:
            ValueError: If the existing configuration file is invalid.
        """
        cls.ensure_config_dir_exists()

        config_file_path = cls.get_config_file_path()

        if not config_file_path.exists():
            # Create a file using the default configuration
            default_config = cls.model_construct(
                version=CONFIG_VERSION,
                profiles={
                    "default": ProfileConfig.model_construct(
                        name="default",
                        api=ApiConfig.model_construct(),
                        user=UserConfig.model_construct(),
                    ),
                },
            )
            default_config.save_to_file()

        config_data = yaml.safe_load(config_file_path.read_text())

        if config_data is None:
            raise ValueError(
                "Invalid credentials.yaml file. Please ensure it is a valid YAML file."
            )

        if "cloud" not in config_data:
            raise ValueError("Invalid credentials.yaml file. Expected a 'cloud' key.")

        try:
            # Previous versions of the arcade cli did not have a version field in credentials.yaml
            # We default to 1 to maintain backwards compatibility.
            config_version = config_data.get("version", "1")
            if config_version == "1":
                return cls.config_constructor_v1(config_data)
            elif config_version == "2":
                return cls.config_constructor_v2(config_data)
            else:
                raise ValueError(
                    f"Invalid credentials.yaml file. Expected version 1 or 2, got '{config_version}'"
                )
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

    @classmethod
    def config_constructor_v1(cls, config_data: dict[str, Any]) -> "Config":
        """
        Instantiate a Config object from a config dictionary with version 1 format.
        """
        # Previous versions of the arcade cli did not have a version field in credentials.yaml
        # We default to 1 to maintain backwards compatibility.
        if config_data.get("version", "1") != "1":
            raise ValueError(
                "Invalid credentials.yaml file. Constructor expected version 1, "
                f"got '{config_data.get('version')}'."
            )

        return cls(
            version=CONFIG_VERSION,
            profiles={
                "default": ProfileConfig.model_construct(
                    name="default",
                    api=ApiConfig.model_construct(**config_data.get("api", {})),
                    user=UserConfig.model_construct(**config_data.get("user", {})),
                ),
            },
        )

    @classmethod
    def config_constructor_v2(cls, config_data: dict[str, Any]) -> "Config":
        """
        Instantiate a Config object from a config dictionary with version 2 format.
        """
        if config_data.get("version") != "2":
            raise ValueError(
                "Invalid credentials.yaml file. Constructor expected version 2, "
                f"got '{config_data.get('version')}'."
            )

        profiles: dict[str, ProfileConfig] = {}
        profiles_data: list[dict[str, Any]] = config_data.get("profiles", [])

        for profile_data in profiles_data:
            try:
                profile_name = profile_data["name"]
            except KeyError:
                raise ValueError(
                    "Invalid credentials.yaml file. Missing a 'name' key in one of the profiles."
                )
            profile_config = ProfileConfig.model_construct(
                name=profile_name,
                api=ApiConfig.model_construct(**profile_data.get("api", {})),
                user=UserConfig.model_construct(**profile_data.get("user", {})),
            )
            profiles[profile_name] = profile_config

        return cls(
            version=CONFIG_VERSION,
            profiles=profiles,
        )

    @staticmethod
    def add_profile(
        profile_name: str,
        api_key: str,
        email: str,
        auto_save: bool = True,
    ) -> "Config":
        """
        Add a profile to the configuration.
        """
        config = Config.load_from_file()
        config.profiles[profile_name] = ProfileConfig.model_construct(
            name=profile_name,
            api=ApiConfig.model_construct(key=api_key),
            user=UserConfig.model_construct(email=email),
        )
        if auto_save:
            config.save_to_file()
        return config

    @staticmethod
    def remove_profile(profile_name: str, auto_save: bool = True) -> "Config":
        """
        Remove a profile from the configuration.
        """
        config = Config.load_from_file()
        del config.profiles[profile_name]
        if auto_save:
            config.save_to_file()
        return config

    def profile(self, profile_name: str = "default") -> ProfileConfig:
        """
        Get a profile from the configuration.
        """
        try:
            return self.profiles[profile_name]
        except KeyError:
            available_profiles = ", ".join(self.profiles.keys())
            raise ValueError(
                f"Profile '{profile_name}' not found in configuration. Available profiles: {available_profiles}"
            )

    def save_to_file(self) -> None:
        """
        Save the configuration to the YAML file in the configuration directory.
        """
        Config.ensure_config_dir_exists()
        config_file_path = Config.get_config_file_path()
        config_file_path.write_text(yaml.dump(self.model_dump()))

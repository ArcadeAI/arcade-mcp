import ipaddress
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import idna
import toml
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


class EngineConfig(BaseConfig):
    """
    Arcade Engine configuration.
    """

    host: str = "api.arcade-ai.com"
    """
    Arcade Engine host.
    """
    port: int | None = None
    """
    Arcade Engine port.
    """
    tls: bool = True
    """
    Whether to use TLS for the connection to Arcade Engine.
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
    engine: EngineConfig | None = EngineConfig()
    """
    Arcade Engine configuration.
    """

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._engine_url_cache: str | None = None
        self._engine_url_cache_key: str | None = None

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
        return cls.get_config_dir_path() / "arcade.toml"

    def _generate_engine_url_cache_key(self) -> str:
        """
        Generate a cache key for the engine_url property, based on its underlying data.
        """
        if self.engine is None:
            return ""

        return f"{self.engine.host}:{self.engine.port}:{self.engine.tls}"

    @property
    def engine_url(self) -> str:
        """
        Get the cached URL of the Arcade Engine.

        This property is cached after its first access to improve performance.
        The cache is automatically invalidated if any of the underlying data changes.

        The port is included in the URL unless the host is a fully qualified domain name
        (excluding IP addresses) and no port is specified. Handles IPv4, IPv6, IDNs, and
        hostnames with underscores.

        This property exists to provide a consistent and correctly formatted URL for
        connecting to the Arcade Engine, taking into account various configuration
        options and edge cases. It ensures that:

        1. The correct protocol (http/https) is used based on the TLS setting.
        2. IPv4 and IPv6 addresses are properly formatted.
        3. Internationalized Domain Names (IDNs) are correctly encoded.
        4. Fully Qualified Domain Names (FQDNs) are identified and handled appropriately.
        5. Ports are included when necessary, respecting common conventions for FQDNs.
        6. Hostnames with underscores (common in development environments) are supported.
        7. Pre-existing port specifications in the host are respected.

        Returns:
            str: The fully constructed URL for the Arcade Engine.

        Raises:
            ValueError: If the engine configuration is missing or incomplete.
        """
        current_cache_key = self._generate_engine_url_cache_key()
        if self._engine_url_cache is None or self._engine_url_cache_key != current_cache_key:
            self._engine_url_cache = self._compute_engine_url()
            self._engine_url_cache_key = current_cache_key
        return self._engine_url_cache

    def _compute_engine_url(self) -> str:
        if self.engine is None:
            raise ValueError("Configuration for Engine is not set in arcade.toml")
        if not self.engine.host:
            raise ValueError("Configuration for Engine host is not set in arcade.toml")

        protocol = "https" if self.engine.tls else "http"

        # Handle potential IDNs
        try:
            encoded_host = idna.encode(self.engine.host).decode("ascii")
        except idna.IDNAError:
            encoded_host = self.engine.host

        # Check if the host is a valid IP address (IPv4 or IPv6)
        try:
            ipaddress.ip_address(encoded_host)
            is_ip = True
        except ValueError:
            is_ip = False

        # Parse the host, handling potential IPv6 addresses
        host_for_parsing = f"[{encoded_host}]" if is_ip and ":" in encoded_host else encoded_host
        parsed_host = urlparse(f"//{host_for_parsing}")

        # Check if the host is a fully qualified domain name (excluding IP addresses)
        is_fqdn = "." in parsed_host.netloc and not is_ip and "_" not in parsed_host.netloc

        # Handle hosts that might already include a port
        if ":" in parsed_host.netloc and not is_ip:
            host, existing_port = parsed_host.netloc.rsplit(":", 1)
            if existing_port.isdigit():
                return f"{protocol}://{parsed_host.netloc}"

        if is_fqdn and self.engine.port is None:
            return f"{protocol}://{encoded_host}"
        elif self.engine.port is not None:
            return f"{protocol}://{encoded_host}:{self.engine.port}"
        else:
            return f"{protocol}://{encoded_host}"

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

        If no configuration file exists, this method will create a new one with default values.
        The default configuration includes:
        - An empty API configuration
        - A default Engine configuration (host: "api.arcade-ai.com", port: None, tls: True)
        - No user configuration

        This behavior ensures that the application always has a valid configuration to work with,
        but it may not be suitable for all use cases. If a specific configuration is required,
        ensure that the configuration file exists before calling this method.

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

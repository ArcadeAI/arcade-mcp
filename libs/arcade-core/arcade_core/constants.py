import os


def arcade_config_path() -> str:
    """Resolve the Arcade configuration directory. Typically ``~/.arcade``.

    ``ARCADE_WORK_DIR`` has historically named the configuration directory
    itself. Keep that meaning and centralize it here so constants and ``Config``
    cannot resolve different credentials files again.
    """
    configured = os.getenv("ARCADE_WORK_DIR")
    if configured:
        return os.path.expanduser(configured)
    return os.path.expanduser("~/.arcade")


# The path to the directory containing the Arcade configuration files. Typically ~/.arcade
ARCADE_CONFIG_PATH = arcade_config_path()
# The path to the file containing the user's Arcade-related credentials (e.g., ARCADE_API_KEY).
CREDENTIALS_FILE_PATH = os.path.join(ARCADE_CONFIG_PATH, "credentials.yaml")

# Host defaults used by both the CLI and MCP server
PROD_COORDINATOR_HOST = "cloud.arcade.dev"
PROD_ENGINE_HOST = "api.arcade.dev"
LOCALHOST = "localhost"

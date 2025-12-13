import os

# The path to the directory containing the Arcade configuration files. Typically ~/.arcade
ARCADE_CONFIG_PATH = os.path.join(os.path.expanduser(os.getenv("ARCADE_WORK_DIR", "~")), ".arcade")
# The path to the file containing the user's Arcade-related credentials (e.g., ARCADE_API_KEY).
CREDENTIALS_FILE_PATH = os.path.join(ARCADE_CONFIG_PATH, "credentials.yaml")

# Host defaults used by both the CLI and MCP server
PROD_COORDINATOR_HOST = "cloud.arcade.dev"
PROD_ENGINE_HOST = "api.arcade.dev"
LOCALHOST = "localhost"

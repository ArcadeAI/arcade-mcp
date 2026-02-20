import warnings

warnings.warn(
    "\n" + "=" * 70 + "\n"
    "DEPRECATION NOTICE: crewai-arcade is no longer maintained.\n"
    "\n"
    "This package has been deprecated. Please visit https://docs.arcade.dev\n"
    "for the latest documentation on integrating Arcade tools into your\n"
    "applications.\n"
    "\n"
    "Arcade now supports MCP (Model Context Protocol) and direct API\n"
    "integration via the Arcade Python SDK.\n" + "=" * 70,
    DeprecationWarning,
    stacklevel=2,
)

__all__: list[str] = []

"""Template utilities for arcade-mcp."""

from pathlib import Path


def get_template_directory() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent
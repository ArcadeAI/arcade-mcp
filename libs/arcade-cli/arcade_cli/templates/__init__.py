from pathlib import Path


def get_minimal_template_directory() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent / "minimal"

def get_full_template_directory() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent / "full"

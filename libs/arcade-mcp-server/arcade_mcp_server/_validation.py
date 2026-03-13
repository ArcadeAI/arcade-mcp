"""Shared validation patterns for arcade-mcp-server."""

import re

# Official semver.org regex (simplified for Python)
# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

# MAJOR.MINOR pattern for normalization to MAJOR.MINOR.0
SHORT_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")

# MAJOR-only pattern for normalization to MAJOR.0.0
MAJOR_ONLY_PATTERN = re.compile(r"^(0|[1-9]\d*)$")


def normalize_version(version: str) -> str:
    """Normalize and validate a version string to canonical semver.
    Raises:
        TypeError: if version is not a string.
        ValueError: if version is empty or not valid semver after normalization.
    """
    if not isinstance(version, str):
        raise TypeError("version must be a string")
    if not version:
        raise ValueError("version cannot be empty")
    # Strip optional v prefix
    if version.startswith("v"):
        version = version[1:]
    # Expand short forms to full MAJOR.MINOR.PATCH
    if MAJOR_ONLY_PATTERN.match(version):
        version = f"{version}.0.0"
    elif SHORT_VERSION_PATTERN.match(version):
        version = f"{version}.0"
    if not SEMVER_PATTERN.match(version):
        raise ValueError(version)
    return version

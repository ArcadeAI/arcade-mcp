"""Shared validation patterns for arcade-mcp-server.

These patterns align with Go's golang.org/x/mod/semver so that versions
validated here will use semver.Compare (correct ordering) in the Engine
rather than falling back to strings.Compare (lexicographic, broken).
"""

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

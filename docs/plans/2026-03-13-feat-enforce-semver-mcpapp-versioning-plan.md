---
title: "Enforce semver for MCPApp versioning"
type: feat
status: active
date: 2026-03-13
---

# Enforce Semver for MCPApp Versioning

## Overview

Add build-time validation to `MCPApp` so that invalid version strings are rejected at instantiation rather than silently flowing through to the Engine, where they cause incorrect version ordering.

## Problem Statement

`MCPApp.__init__` accepts any string as `version` with zero validation. The version propagates to:

1. `MCPSettings.server.version` (Pydantic model)
2. The MCP `initialize` response `serverInfo.version` sent to clients
3. `toolkit_version` when registering tools in the catalog

The Engine's Go codebase (`apps/engine/pkg/tool/registry.go`) uses `golang.org/x/mod/semver` to compare toolkit versions. When both versions are valid semver, `semver.Compare` produces correct ordering. When either version is **not** valid semver, it falls back to `strings.Compare` (lexicographic), which produces **incorrect ordering** — e.g., `1.10.0 < 1.9.0`.

The Engine never rejects bad versions — it sanitizes them via `parseVersion()` (stripping non-ASCII chars) and uses `"0.0.0"` as a fallback. This means broken versions silently degrade the system rather than failing loudly.

## Proposed Solution

Validate `version` at `MCPApp` instantiation time using a semver regex that matches what Go's `semver.IsValid("v" + version)` accepts. This ensures every version that reaches the Engine will take the correct `semver.Compare` path.

### Why semver regex (not `packaging.version.Version`)

`packaging.version.Version` validates **PEP 440**, not semver. These are materially different:

| Version string    | PEP 440 valid? | Go `semver.IsValid`? |
|-------------------|----------------|----------------------|
| `1.0.0`           | Yes            | Yes                  |
| `1.0.0.post1`     | Yes            | **No**               |
| `1.0.0dev`        | Yes            | **No**               |
| `1.0.0a1`         | Yes            | **No**               |
| `1.0.0-alpha.1`   | **No**         | Yes                  |
| `1.0.0+build.123` | Yes (ignored)  | Yes                  |

Using PEP 440 would accept versions the Engine can't compare correctly and reject versions the Engine handles fine. A semver regex aligns perfectly with the Engine's actual behavior.

### The semver regex

Use the official [semver.org](https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string) regex, simplified for Python:

```python
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
```

No external dependency required — this is a compile-time constant.

### Normalization of short versions

`"1.0"` (MAJOR.MINOR) is a common version format. Instead of rejecting it, **normalize** it to `"1.0.0"` before validation. This ensures the Engine uses `semver.Compare` (correct ordering) rather than falling back to `strings.Compare` (lexicographic, broken for multi-digit components).

A secondary regex detects the `MAJOR.MINOR` pattern:

```python
SHORT_VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)
```

If the version matches `SHORT_VERSION_PATTERN`, append `.0` before running the full semver check. The **normalized** value is what gets stored and propagated.

## Technical Approach

### Files to modify

| File | Change |
|------|--------|
| `libs/arcade-mcp-server/arcade_mcp_server/mcp_app.py` | Add `_validate_version()`, store as `self._version`, add `@property` + setter |
| `libs/arcade-mcp-server/arcade_mcp_server/settings.py` | Add `field_validator("version")` to `ServerSettings`, fix default from `"0.1.0dev"` to `"0.1.0"` |
| `libs/tests/arcade_mcp_server/test_mcp_app.py` | Add parametrized tests for valid/invalid versions |
| `libs/arcade-mcp-server/pyproject.toml` | Bump version (patch) |

### Implementation details

#### 1. `_validate_version()` in `mcp_app.py`

Mirror the existing `_validate_name()` pattern exactly:

```python
# libs/arcade-mcp-server/arcade_mcp_server/mcp_app.py

SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

SHORT_VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)

def _validate_version(self, version: str) -> str:
    if not isinstance(version, str):
        raise TypeError("MCPApp's version must be a string")
    if not version:
        raise ValueError("MCPApp's version cannot be empty")
    if version.startswith("v"):
        raise ValueError(
            f"MCPApp's version must not include a 'v' prefix. "
            f"Use '{version[1:]}' instead of '{version}'"
        )
    # Normalize MAJOR.MINOR → MAJOR.MINOR.0
    if SHORT_VERSION_PATTERN.match(version):
        version = f"{version}.0"
    if not SEMVER_PATTERN.match(version):
        raise ValueError(
            f"MCPApp's version must be a valid semver string "
            f"(e.g., '1.0.0', '1.2.3-beta.1'), got '{version}'"
        )
    return version
```

In `__init__`:

```python
self._version = self._validate_version(version)
```

Property + setter (mirroring `name`):

```python
@property
def version(self) -> str:
    return self._version

@version.setter
def version(self, value: str) -> None:
    self._version = self._validate_version(value)
```

All existing references to `self.version` continue to work via the property.

#### 2. `ServerSettings.version` field_validator in `settings.py`

```python
# libs/arcade-mcp-server/arcade_mcp_server/settings.py

@field_validator("version")
@classmethod
def validate_version(cls, v: str) -> str:
    if not SEMVER_PATTERN.match(v):
        raise ValueError(
            f"Server version must be a valid semver string "
            f"(e.g., '1.0.0'), got '{v}'"
        )
    return v
```

Also change the default from `"0.1.0dev"` to `"0.1.0"`.

The `SEMVER_PATTERN` regex should be extracted to a shared location (e.g., a `_validation.py` module in `arcade_mcp_server/`) to avoid duplication between `mcp_app.py` and `settings.py`.

#### 3. Tests in `test_mcp_app.py`

Follow the existing parametrized test pattern:

```python
@pytest.mark.parametrize(
    "version,expected_result",
    [
        # Full semver (passthrough)
        ("1.0.0", "1.0.0"),
        ("0.1.0", "0.1.0"),
        ("0.0.0", "0.0.0"),
        ("10.20.30", "10.20.30"),
        # Pre-release and build metadata
        ("1.2.3-alpha.1", "1.2.3-alpha.1"),
        ("1.2.3+build.456", "1.2.3+build.456"),
        ("1.2.3-beta.1+build.789", "1.2.3-beta.1+build.789"),
        # Short versions (normalized to MAJOR.MINOR.0)
        ("1.0", "1.0.0"),
        ("0.1", "0.1.0"),
        ("2.5", "2.5.0"),
        ("10.20", "10.20.0"),
    ],
)
def test_validate_version_valid_versions(self, version, expected_result):
    app = MCPApp()
    result = app._validate_version(version)
    assert result == expected_result


@pytest.mark.parametrize(
    "version,expected_error",
    [
        ("", ValueError),
        (None, TypeError),
        (123, TypeError),
        ([], TypeError),
        ({}, TypeError),
        ("v1.0.0", ValueError),         # v prefix
        ("1", ValueError),               # missing minor+patch
        ("1.0.0.0", ValueError),         # too many components
        ("1.0.0dev", ValueError),        # PEP 440 dev (not semver)
        ("1.0.0a1", ValueError),         # PEP 440 alpha (not semver)
        ("1.0.0.post1", ValueError),     # PEP 440 post (not semver)
        ("not_a_version", ValueError),   # garbage
        ("latest", ValueError),          # word
        (" 1.0.0", ValueError),          # leading space
        ("1.0.0 ", ValueError),          # trailing space
        ("01.0.0", ValueError),          # leading zero
    ],
)
def test_validate_version_invalid_versions(self, version, expected_error):
    app = MCPApp()
    with pytest.raises(expected_error):
        app._validate_version(version)
```

Also add integration tests:

```python
def test_mcp_app_rejects_invalid_version_at_init(self):
    with pytest.raises(ValueError, match="semver"):
        MCPApp(name="TestApp", version="not-valid")

def test_mcp_app_rejects_invalid_version_via_setter(self):
    app = MCPApp(name="TestApp", version="1.0.0")
    with pytest.raises(ValueError, match="semver"):
        app.version = "bad"
```

## Acceptance Criteria

- [ ] `MCPApp(version="not-valid")` raises `ValueError` at instantiation
- [ ] `MCPApp(version=123)` raises `TypeError` at instantiation
- [ ] `MCPApp(version="v1.0.0")` raises `ValueError` with a helpful message suggesting `"1.0.0"`
- [ ] `MCPApp(version="1.0.0")` works (no change in behavior)
- [ ] `MCPApp(version="1.0")` works and normalizes to `"1.0.0"` (short version support)
- [ ] `MCPApp(version="1.0.0-alpha.1")` works (pre-release is valid semver)
- [ ] `MCPApp(version="1.0.0+build.123")` works (build metadata is valid semver)
- [ ] `app.version = "bad"` raises `ValueError` (property setter validates)
- [ ] `ServerSettings(version="bad")` raises `ValidationError` (Pydantic validator)
- [ ] `ServerSettings()` default is `"0.1.0"` (not `"0.1.0dev"`)
- [ ] All existing tests pass (existing versions like `"1.0.0"`, `"1.5.0"`, `"3.0.0"` are valid semver)
- [ ] Parametrized tests cover the valid/invalid version matrix above
- [ ] `arcade-mcp-server` version in `pyproject.toml` is bumped (patch)

## Dependencies & Risks

**Risk: Existing users with non-semver versions.** Any user currently passing a PEP 440 or arbitrary version string will get an error on upgrade. This is intentional — their versions were silently causing incorrect ordering in the Engine.

**Risk: `ServerSettings` default change.** The default changes from `"0.1.0dev"` to `"0.1.0"`. Any test asserting the old default needs updating. Search for `"0.1.0dev"` in the test suite.

**Risk: Env var `MCP_SERVER_VERSION`.** The `field_validator` on `ServerSettings` covers this path — if someone sets `MCP_SERVER_VERSION=bad` in their environment, it will now fail at settings construction time.

**Out of scope (but noted for future):**
- `ARCADE_MCP_SERVER_VERSION` env var in `worker.py` — separate code path, separate PR
- `build_minimal_toolkit` default `"0.1.0dev"` in `arcade_core/discovery.py` — separate PR
- Version propagation to `_mcp_settings` on setter mutation — mirrors existing `name` limitation

## References

### arcade-mcp (this repo)

- `MCPApp.__init__`: `libs/arcade-mcp-server/arcade_mcp_server/mcp_app.py:72-103`
- `_validate_name()` pattern: `libs/arcade-mcp-server/arcade_mcp_server/mcp_app.py:137-175`
- `ServerSettings.version`: `libs/arcade-mcp-server/arcade_mcp_server/settings.py:158-161`
- `field_validator` examples: `libs/arcade-mcp-server/arcade_mcp_server/settings.py:262-270`
- Existing tests: `libs/tests/arcade_mcp_server/test_mcp_app.py`

### Engine (monorepo)

- `compareToolVersions` (semver comparison with fallback): `apps/engine/pkg/tool/registry.go:117-130`
- `parseVersion` (sanitization, not validation): `apps/engine/internal/directors/workers/config/mcp.go:506-523`
- `Name.Validate` (loose ASCII check): `apps/engine/pkg/tool/tool.go:207-211`
- `toolkits` table schema: `apps/engine/pkg/storage/migrations/postgres/000041_tool_tables.up.sql`
- Go semver library: `golang.org/x/mod/semver` v0.33.0

### External

- semver.org specification: https://semver.org/
- Official semver regex: https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string

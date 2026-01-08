# Installation Tests

This directory contains tests to verify that `arcade-mcp` can be installed from source and works correctly across different platforms.

## Overview

The installation test (`test_install.py`) verifies:

1. **Prerequisites**: Checks that required tools (like `uv`) are available
2. **Installation**: Installs `arcade-mcp` from source using `uv`
3. **CLI Functionality**: Tests that the `arcade` CLI command is available and working
4. **File Locking**: Verifies cross-platform file locking with `portalocker` (replacing `fcntl`)

## Running Locally

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) installed and available in PATH

### Quick Start

From the project root:

```bash
uv run python tests/install/test_install.py
```

Or if you have the package already installed:

```bash
python tests/install/test_install.py
```

### Direct Execution

The script is executable, so you can also run it directly:

```bash
./tests/install/test_install.py
```

Or with Python:

```bash
python3 tests/install/test_install.py
```

## What the Test Does

1. **Checks Prerequisites**
   - Verifies `uv` is installed and available

2. **Installs Package**
   - Syncs dependencies with `uv sync --dev`
   - Installs `arcade-mcp` in editable mode from source

3. **Tests CLI**
   - Verifies `arcade --help` works
   - Tests `arcade --version` (optional)
   - Tests `arcade whoami` (may fail if not logged in, but shouldn't crash)

4. **Tests File Locking**
   - Creates a temporary identity file
   - Tests shared lock for reading
   - Tests exclusive lock for writing
   - Verifies `portalocker` works cross-platform (Windows, macOS, Linux)

## Expected Output

On success, you should see:

```
============================================================
Testing arcade-mcp Installation from Source
============================================================

Project root: /path/to/arcade-mcp

============================================================
Prerequisites Check
============================================================
✅ Success: Check uv availability

============================================================
Installation Phase
============================================================
✅ Success: Sync dependencies with uv
✅ Success: Install arcade-mcp from source (editable mode)

============================================================
CLI Functionality Tests
============================================================
✅ Success: Verify arcade CLI is available (--help)
✅ Success: Check arcade version
✅ Success: Test whoami command (no auth required)

============================================================
File Locking Tests (portalocker)
============================================================
✅ Success: Test portalocker file locking (cross-platform)

============================================================
Test Summary
============================================================
✅ PASSED: Check uv availability
✅ PASSED: Sync dependencies with uv
✅ PASSED: Install arcade-mcp from source (editable mode)
✅ PASSED: Verify arcade CLI is available (--help)
...

Total: X/X tests passed

🎉 All tests passed! arcade-mcp is working correctly.
```

## Running in CI/CD

This test is automatically run in GitHub Actions on:
- macOS (latest)
- Windows (latest)
- Linux (Ubuntu latest)

For Python versions: 3.10, 3.11, and 3.12

See `.github/workflows/test-install.yml` for the CI configuration.

## Troubleshooting

### `uv` not found

If you get an error that `uv` is not available:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or using pip:

```bash
pip install uv
```

### Permission Denied

If you get a permission error when running the script directly:

```bash
chmod +x tests/install/test_install.py
```

### Import Errors

If you see import errors, make sure you're running from the project root and that dependencies are installed:

```bash
uv sync --dev
```

## Related Files

- `.github/workflows/test-install.yml` - GitHub Actions workflow
- `libs/arcade-core/arcade_core/usage/identity.py` - File locking implementation using `portalocker`

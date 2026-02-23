# Installation Tests

This directory contains tests to verify that `arcade-mcp` can be installed from source and works correctly across different platforms.

## Overview

The installation test (`test_install.py`) verifies:

1. **Prerequisites**: Checks that required tools (like `uv`) are available
2. **Installation**: Installs `arcade-mcp` from source using `uv`
3. **CLI Functionality**: Tests that the `arcade` CLI command is available and working
4. **File Locking**: Verifies cross-platform file locking with `portalocker` (replacing `fcntl`)
5. **CLI Configure**: Writes temp config files for Cursor, VS Code, and Claude
6. **CLI New Scaffold**: Creates a minimal server in a path with spaces

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
   - Syncs dependencies with `uv sync --extra dev`
   - Installs `arcade-mcp` in editable mode from source

3. **Tests CLI**
   - Verifies `arcade --help` works
   - Tests `arcade --version` (optional)
   - Tests `arcade whoami` (may fail if not logged in, but shouldn't crash)

4. **Tests CLI Configure**
   - Runs `arcade configure` for Cursor, VS Code, and Claude using `--config`
   - Verifies JSON structure for stdio/http configurations

5. **Tests CLI New Scaffold**
   - Runs `arcade new` in a temp path with spaces
   - Verifies expected files and directories are created

6. **Tests File Locking**
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
CLI Configure Tests
============================================================
✅ Success: Configure Cursor (stdio) with temp config
✅ Success: Configure Cursor (http) with temp config
✅ Success: Configure VS Code (stdio) with temp config
✅ Success: Configure VS Code (http) with temp config
✅ Success: Configure Claude (stdio) with temp config

============================================================
CLI New Scaffold Tests
============================================================
✅ Success: Scaffold new server in path with spaces

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

### Windows: `uv` installed but still not found

On some Windows shells, `uv` is installed to `C:\Users\<user>\.local\bin` but
the current session PATH is not refreshed automatically. In PowerShell:

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv --version
```

### Permission Denied

If you get a permission error when running the script directly:

```bash
chmod +x tests/install/test_install.py
```

### Import Errors

If you see import errors, make sure you're running from the project root and that dependencies are installed:

```bash
uv sync --extra dev
```

### Optional eval/display test dependencies

Some CLI test files (for eval/display formatting paths) require optional eval
dependencies such as `openai`, `pytz`, and `numpy`. Install the eval extras
before running those suites:

```bash
uv sync --extra dev --extra evals
```

## Related Files

- `.github/workflows/test-install.yml` - GitHub Actions workflow
- `libs/arcade-core/arcade_core/usage/identity.py` - File locking implementation using `portalocker`
- `reports/windows-manual-test-checklist.md` - Windows manual validation steps

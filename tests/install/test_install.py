#!/usr/bin/env python3
"""
Test script to verify arcade-mcp installation from source.

This script:
1. Installs arcade-mcp from source using uv
2. Runs basic CLI commands to verify functionality
3. Tests cross-platform compatibility (file locking with portalocker)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 encoding for cross-platform compatibility (especially Windows)
if sys.platform == "win32":
    # Set UTF-8 encoding for Windows console
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    # Set environment variable for subprocesses
    os.environ["PYTHONIOENCODING"] = "utf-8"


class TestRunner:
    """Organizes and runs installation tests for arcade-mcp."""

    def __init__(self, project_root: Path):
        """Initialize test runner with project root."""
        self.project_root = project_root
        self.arcade_cmd = self._find_arcade_command()
        self.test_results: list[tuple[str, bool]] = []

    def _find_arcade_command(self) -> list[str]:
        """Find the arcade command (either direct or via uv run)."""
        if shutil.which("arcade"):
            return ["arcade"]
        return ["uv", "run", "arcade"]

    def run_command(
        self, cmd: list[str], description: str, required: bool = True
    ) -> tuple[bool, str]:
        """Run a command and return success status and output."""
        print(f"\n{'=' * 60}")
        print(f"Testing: {description}")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'=' * 60}")

        # Ensure UTF-8 encoding for cross-platform compatibility (especially Windows)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
                env=env,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout: {description}")
            self.test_results.append((description, False))
            return False, "Command timed out"
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed: {description}")
            print(f"Return code: {e.returncode}")
            if e.stdout:
                print(f"Stdout:\n{e.stdout}")
            if e.stderr:
                print(f"Stderr:\n{e.stderr}")
            self.test_results.append((description, False))
            if required:
                return False, e.stderr or e.stdout or ""
            return False, e.stderr or e.stdout or ""
        except Exception as e:
            print(f"❌ Error: {description}")
            print(f"Exception: {e}")
            self.test_results.append((description, False))
            if required:
                return False, str(e)
            return False, str(e)
        else:
            print(f"✅ Success: {description}")
            if result.stdout:
                print(f"Output:\n{result.stdout}")
            self.test_results.append((description, True))
            output = result.stdout
            return True, output

    def check_prerequisites(self) -> bool:
        """Check that required tools are available."""
        print("\n" + "=" * 60)
        print("Prerequisites Check")
        print("=" * 60)

        success, _ = self.run_command(["uv", "--version"], "Check uv availability", required=True)
        return success

    def install_package(self) -> bool:
        """Install arcade-mcp from source."""
        print("\n" + "=" * 60)
        print("Installation Phase")
        print("=" * 60)

        # Sync dependencies
        sync_success, _ = self.run_command(
            ["uv", "sync", "--dev"],
            "Sync dependencies with uv",
            required=True,
        )
        if not sync_success:
            return False

        # Install package in editable mode
        install_success, _ = self.run_command(
            ["uv", "pip", "install", "-e", str(self.project_root)],
            "Install arcade-mcp from source (editable mode)",
            required=True,
        )
        return install_success

    def test_cli_availability(self) -> bool:
        """Test that the CLI is available and working."""
        print("\n" + "=" * 60)
        print("CLI Functionality Tests")
        print("=" * 60)

        # Test --help
        help_success, _ = self.run_command(
            [*self.arcade_cmd, "--help"],
            "Verify arcade CLI is available (--help)",
            required=True,
        )
        if not help_success:
            return False

        # Test --version (optional, might not exist)
        self.run_command(
            [*self.arcade_cmd, "--version"],
            "Check arcade version",
            required=False,
        )

        # Test whoami (might fail if not logged in, but shouldn't crash)
        self.run_command(
            [*self.arcade_cmd, "whoami"],
            "Test whoami command (no auth required)",
            required=False,
        )

        return True

    def test_file_locking(self) -> bool:
        """Test cross-platform file locking with portalocker."""
        print("\n" + "=" * 60)
        print("File Locking Tests (portalocker)")
        print("=" * 60)

        test_code = """
import tempfile
import json
from pathlib import Path
from arcade_core.usage.identity import UsageIdentity
import os

# Create a temporary directory for testing
with tempfile.TemporaryDirectory() as tmpdir:
    # Monkey patch the config path
    import arcade_core.usage.identity as identity_module
    original_path = identity_module.ARCADE_CONFIG_PATH
    identity_module.ARCADE_CONFIG_PATH = tmpdir

    try:
        # Create identity instance and test file operations
        identity = UsageIdentity()

        # Test load_or_create (uses file locking)
        data1 = identity.load_or_create()
        assert "anon_id" in data1
        print(f"✅ Successfully created identity with anon_id: {data1['anon_id']}")

        # Test that we can read it back (uses shared lock)
        identity2 = UsageIdentity()
        data2 = identity2.load_or_create()
        assert data2["anon_id"] == data1["anon_id"]
        print(f"✅ Successfully read identity with file locking")

        # Test atomic write (uses exclusive lock)
        identity.set_linked_principal_id("test-principal-123")
        data3 = identity.load_or_create()
        assert data3["linked_principal_id"] == "test-principal-123"
        print(f"✅ Successfully wrote identity with file locking")

        print("✅ All portalocker file locking tests passed!")
    finally:
        identity_module.ARCADE_CONFIG_PATH = original_path
"""

        # Use uv run to ensure we're in the right environment
        python_cmd = ["uv", "run", "python", "-c", test_code]
        success, _ = self.run_command(
            python_cmd,
            "Test portalocker file locking (cross-platform)",
            required=True,
        )
        return success

    def run_all_tests(self) -> int:
        """Run all tests and return exit code."""
        print("=" * 60)
        print("Testing arcade-mcp Installation from Source")
        print("=" * 60)
        print(f"\nProject root: {self.project_root}")

        # Run test phases
        test_phases = [
            ("Prerequisites", self.check_prerequisites),
            ("Installation", self.install_package),
            ("CLI Functionality", self.test_cli_availability),
            ("File Locking", self.test_file_locking),
        ]

        for phase_name, test_func in test_phases:
            if not test_func():
                print(f"\n❌ {phase_name} phase failed. Stopping tests.")
                return 1

        # Print summary
        self.print_summary()
        return 0

    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)

        passed = sum(1 for _, success in self.test_results if success)
        total = len(self.test_results)

        for description, success in self.test_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status}: {description}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 All tests passed! arcade-mcp is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed.")


def main() -> int:
    """Main entry point."""
    # Get project root (two levels up from tests/install/)
    project_root = Path(__file__).parent.parent.parent.absolute()
    runner = TestRunner(project_root)
    return runner.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())

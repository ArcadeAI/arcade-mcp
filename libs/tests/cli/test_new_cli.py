from io import StringIO
from pathlib import Path

import pytest
from arcade_cli.new import create_new_toolkit_minimal
from rich.console import Console


def test_create_new_toolkit_minimal_with_spaces(tmp_path: Path) -> None:
    output_dir = tmp_path / "dir with spaces"
    output_dir.mkdir()

    create_new_toolkit_minimal(str(output_dir), "my_server")

    server_root = output_dir / "my_server"
    assert (server_root / "pyproject.toml").is_file()
    assert (server_root / "src" / "my_server" / "server.py").is_file()
    assert (server_root / ".env.example").is_file()


def test_create_new_toolkit_minimal_prints_next_steps(tmp_path: Path) -> None:
    """After scaffolding, the CLI should print 'Next steps' guidance."""
    output_dir = tmp_path / "scaffold_test"
    output_dir.mkdir()

    # Capture console output by replacing the module-level console.
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)

    import arcade_cli.new as new_mod

    orig = new_mod.console
    new_mod.console = test_console
    try:
        create_new_toolkit_minimal(str(output_dir), "demo_srv")
    finally:
        new_mod.console = orig

    output = buf.getvalue()
    assert "Next steps:" in output, f"Expected 'Next steps:' in output:\n{output}"
    assert "uv run server.py" in output, f"Expected 'uv run server.py' in output:\n{output}"
    assert "demo_srv" in output, f"Expected toolkit name in output:\n{output}"


def test_create_new_toolkit_minimal_rejects_duplicate(tmp_path: Path) -> None:
    """Creating a toolkit with a name that already exists should raise."""
    output_dir = tmp_path / "dup_test"
    output_dir.mkdir()

    create_new_toolkit_minimal(str(output_dir), "my_srv")

    with pytest.raises(FileExistsError, match="already exists"):
        create_new_toolkit_minimal(str(output_dir), "my_srv")


def test_create_new_toolkit_minimal_rejects_invalid_name(tmp_path: Path) -> None:
    """Toolkit names with invalid characters should raise ValueError."""
    output_dir = tmp_path / "invalid_test"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="illegal characters"):
        create_new_toolkit_minimal(str(output_dir), "My-Server!")

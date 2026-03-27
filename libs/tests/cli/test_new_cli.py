from io import StringIO
from pathlib import Path

import pytest
from arcade_cli.new import create_new_toolkit, create_new_toolkit_minimal
from rich.console import Console


def test_create_new_toolkit_prints_next_steps(tmp_path: Path) -> None:
    """create_new_toolkit (full template) should print numbered next steps."""
    output_dir = tmp_path / "full_test"
    output_dir.mkdir()

    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)
    import arcade_cli.new as new_mod

    orig = new_mod.console
    new_mod.console = test_console
    try:
        create_new_toolkit(str(output_dir), "my_server")
    finally:
        new_mod.console = orig

    output = buf.getvalue()
    assert "Next steps:" in output
    assert "1. cd " in output
    assert "make install" in output
    assert "make dev" in output
    assert "make test" in output
    assert "my_server" in output


def test_create_new_toolkit_full_template_matches_monorepo(tmp_path: Path) -> None:
    """Full template should produce files matching monorepo conventions."""
    output_dir = tmp_path / "full_conventions"
    output_dir.mkdir()

    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)
    import arcade_cli.new as new_mod

    orig = new_mod.console
    new_mod.console = test_console
    try:
        create_new_toolkit(str(output_dir), "my_server")
    finally:
        new_mod.console = orig

    toolkit_dir = output_dir / "my_server"

    # .ruff.toml should extend monorepo root config
    ruff_toml = (toolkit_dir / ".ruff.toml").read_text()
    assert ruff_toml.strip() == 'extend = "../../../../ruff.toml"'

    # .pre-commit-config.yaml should use ruff-check and v0.15.7
    pre_commit = (toolkit_dir / ".pre-commit-config.yaml").read_text()
    assert "v0.15.7" in pre_commit
    assert "ruff-check" in pre_commit
    assert "id: ruff\n" not in pre_commit

    # pyproject.toml formatting checks
    pyproject = (toolkit_dir / "pyproject.toml").read_text()
    assert 'requires = ["hatchling"]' in pyproject
    assert 'license = { text = "Proprietary' in pyproject
    assert 'asyncio_mode = "auto"' in pyproject
    assert "disallow_untyped_defs = true" in pyproject
    assert '"True"' not in pyproject

    # Makefile should not have pre-commit install
    makefile = (toolkit_dir / "Makefile").read_text()
    assert "pre-commit install" not in makefile

    # .gitignore and README.md should exist
    assert (toolkit_dir / ".gitignore").is_file()
    assert (toolkit_dir / "README.md").is_file()
    readme = (toolkit_dir / "README.md").read_text()
    assert "My Server" in readme


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
    assert "1. cd " in output, f"Expected numbered step 1 in output:\n{output}"
    assert "2. Run the server (choose one transport):" in output, (
        f"Expected numbered step 2 in output:\n{output}"
    )
    assert "- stdio: uv run server.py" in output, f"Expected stdio option in output:\n{output}"
    assert "- http:  uv run server.py --transport http --port 8000" in output, (
        f"Expected HTTP option in output:\n{output}"
    )
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

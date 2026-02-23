#!/usr/bin/env python3
"""Cross-platform no-auth CLI integration smoke checks.

This script runs a minimal but meaningful no-auth integration flow across all
CI operating systems:
1. Validate `arcade configure` writes client configs in a path with spaces.
2. Scaffold a new toolkit with `arcade new`.
3. Run protocol smoke checks (stdio + http) against the generated server.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=capture_output,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout or ''}\nSTDERR:\n{proc.stderr or ''}"
        )
    return proc


def _ensure_exists(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"Expected path to exist: {path}")


def _add_local_uv_sources(pyproject_path: Path, repo_root: Path) -> None:
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    if "[tool.uv.sources]" in pyproject_text:
        return

    repo = repo_root.resolve()
    block_lines = [
        "[tool.uv.sources]",
        f'arcade-mcp = {{ path = "{repo.as_posix()}", editable = true }}',
        f'arcade-mcp-server = {{ path = "{(repo / "libs/arcade-mcp-server").as_posix()}", editable = true }}',
        f'arcade-core = {{ path = "{(repo / "libs/arcade-core").as_posix()}", editable = true }}',
        f'arcade-serve = {{ path = "{(repo / "libs/arcade-serve").as_posix()}", editable = true }}',
        f'arcade-tdk = {{ path = "{(repo / "libs/arcade-tdk").as_posix()}", editable = true }}',
    ]
    pyproject_path.write_text(
        pyproject_text.rstrip() + "\n\n" + "\n".join(block_lines) + "\n",
        encoding="utf-8",
    )


def _run_configure_smoke(repo_root: Path) -> None:
    config_tmp = Path(tempfile.mkdtemp(prefix="arcade mcp config test "))
    try:
        (config_tmp / "server.py").write_text("print('ok')\n", encoding="utf-8")

        cursor_cfg = config_tmp / "cursor config.json"
        vscode_cfg = config_tmp / "vscode config.json"
        claude_cfg = config_tmp / "claude config.json"

        _run(
            [
                "uv",
                "run",
                "--project",
                str(repo_root),
                "arcade",
                "configure",
                "cursor",
                "--name",
                "demo",
                "--config",
                str(cursor_cfg),
            ],
            cwd=config_tmp,
        )

        overwrite = _run(
            [
                "uv",
                "run",
                "--project",
                str(repo_root),
                "arcade",
                "configure",
                "cursor",
                "--transport",
                "http",
                "--port",
                "8123",
                "--name",
                "demo",
                "--config",
                str(cursor_cfg),
            ],
            cwd=config_tmp,
            capture_output=True,
        )
        overwrite_output = (overwrite.stdout or "") + "\n" + (overwrite.stderr or "")
        if "overwrite" not in overwrite_output.lower():
            raise RuntimeError(
                "Expected overwrite warning when configuring cursor with same --name.\n"
                f"Output:\n{overwrite_output}"
            )

        _run(
            [
                "uv",
                "run",
                "--project",
                str(repo_root),
                "arcade",
                "configure",
                "vscode",
                "--name",
                "demo",
                "--config",
                str(vscode_cfg),
            ],
            cwd=config_tmp,
        )
        _run(
            [
                "uv",
                "run",
                "--project",
                str(repo_root),
                "arcade",
                "configure",
                "claude",
                "--name",
                "demo",
                "--config",
                str(claude_cfg),
            ],
            cwd=config_tmp,
        )

        json.loads(cursor_cfg.read_text(encoding="utf-8"))
        json.loads(vscode_cfg.read_text(encoding="utf-8"))
        json.loads(claude_cfg.read_text(encoding="utf-8"))
    finally:
        shutil.rmtree(config_tmp, ignore_errors=True)


def _run_scaffold_and_protocol_smoke(repo_root: Path) -> None:
    scaffold_dir = Path(tempfile.mkdtemp(prefix="arcade scaffold with spaces "))
    try:
        created = _run(
            [
                "uv",
                "run",
                "arcade",
                "new",
                "my_server",
                "--dir",
                str(scaffold_dir),
            ],
            cwd=repo_root,
            capture_output=True,
        )
        new_output = (created.stdout or "") + "\n" + (created.stderr or "")
        if "Next steps:" not in new_output:
            raise RuntimeError(
                "Expected 'Next steps:' output from 'arcade new'.\n" f"Output:\n{new_output}"
            )

        generated_root = scaffold_dir / "my_server"
        _ensure_exists(generated_root / "pyproject.toml")
        _ensure_exists(generated_root / "src" / "my_server" / "server.py")
        _ensure_exists(generated_root / "src" / "my_server" / ".env.example")

        generated_pyproject = generated_root / "pyproject.toml"
        _add_local_uv_sources(generated_pyproject, repo_root)

        generated_server_dir = generated_root / "src" / "my_server"
        _run(
            ["uv", "run", "python", "-c", "import server; print('generated server import ok')"],
            cwd=generated_server_dir,
        )

        _run(
            [
                "uv",
                "run",
                "python",
                "tests/integration/windows/mcp_protocol_smoke.py",
                "--server-dir",
                str(generated_server_dir),
                "--transport",
                "both",
            ],
            cwd=repo_root,
        )
    finally:
        shutil.rmtree(scaffold_dir, ignore_errors=True)


def main() -> None:
    repo_root = Path.cwd().resolve()
    print(f"Repo root: {repo_root}")
    _run(["uv", "--version"], cwd=repo_root)

    _run_configure_smoke(repo_root)
    _run_scaffold_and_protocol_smoke(repo_root)

    print("Cross-platform no-auth CLI smoke checks passed.")


if __name__ == "__main__":
    main()

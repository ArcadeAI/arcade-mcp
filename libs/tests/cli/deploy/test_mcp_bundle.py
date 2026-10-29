"""The bundle an MCP server deploy uploads."""

import base64
import io
import json
import tarfile
from pathlib import Path

from arcade_cli.deploy import create_mcp_bundle, create_package_archive


def write(project: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return project


def members(archive: str) -> dict[str, bytes]:
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(archive)), mode="r:gz") as tar:
        return {
            member.name: tar.extractfile(member).read()  # type: ignore[union-attr]
            for member in tar.getmembers()
            if member.isfile()
        }


def project(tmp_path: Path) -> Path:
    return write(
        tmp_path / "srv",
        {
            "pyproject.toml": "[project]\nname = 'srv'\n",
            "uv.lock": "version = 1\n",
            "server.py": "print('hi')\n",
            "build/__init__.py": "",
            "src/srv/build/tools.py": "",
            "dist/srv-0.1.tar.gz": "",
            ".env": "OPENAI_API_KEY=sk-secret\n",
            ".git/config": "",
            ".venv/pyvenv.cfg": "home = /usr\n",
            "env/pyvenv.cfg": "home = /usr\n",
            "env/lib/site.py": "",
            "src/srv/__pycache__/server.cpython-312.pyc": "",
            "src/srv.egg-info/PKG-INFO": "",
            ".arcade/deploy.json": '{"path": "/stale"}',
        },
    )


class TestMCPBundle:
    def test_the_lock_and_source_ship(self, tmp_path: Path) -> None:
        files = members(create_mcp_bundle(project(tmp_path)))

        assert {"srv/pyproject.toml", "srv/uv.lock", "srv/server.py"} <= set(files)

    def test_a_package_named_build_or_dist_ships(self, tmp_path: Path) -> None:
        files = members(create_mcp_bundle(project(tmp_path)))

        assert "srv/build/__init__.py" in files
        assert "srv/src/srv/build/tools.py" in files
        assert "srv/dist/srv-0.1.tar.gz" in files

    def test_secrets_environments_and_caches_stay_behind(self, tmp_path: Path) -> None:
        names = set(members(create_mcp_bundle(project(tmp_path))))

        for left_out in (".env", ".git/config", ".venv/pyvenv.cfg", "env/pyvenv.cfg"):
            assert f"srv/{left_out}" not in names
        assert not any("__pycache__" in name or ".egg-info" in name for name in names)
        assert not any(name.startswith("srv/env/") for name in names)

    def test_the_runner_settings_are_written_and_the_authors_copy_replaced(
        self, tmp_path: Path
    ) -> None:
        settings = json.dumps({"path": "/api/mcp"}) + "\n"

        files = members(create_mcp_bundle(project(tmp_path), runner_settings=settings))

        assert json.loads(files["srv/.arcade/deploy.json"]) == {"path": "/api/mcp"}

    def test_no_runner_settings_means_no_settings_file(self, tmp_path: Path) -> None:
        files = members(create_mcp_bundle(project(tmp_path)))

        assert "srv/.arcade/deploy.json" not in files


class TestArcadeArchiveUnchanged:
    def test_an_arcade_archive_still_drops_locks_build_and_hidden_files(
        self, tmp_path: Path
    ) -> None:
        names = set(members(create_package_archive(project(tmp_path))))

        assert "srv/uv.lock" not in names
        assert "srv/build/__init__.py" not in names
        assert "srv/.env" not in names
        assert "srv/server.py" in names

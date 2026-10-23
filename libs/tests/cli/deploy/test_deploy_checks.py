"""Checks on a project before it deploys: protocol, dependencies, Python version (DEP-393)."""

from pathlib import Path

import pytest
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy_checks import (
    ProjectCheckError,
    check_project,
    detect_protocol,
    install_source,
)

PY312 = [DeploymentsRunner(language="python", version="3.12", platform="musllinux_1_2")]


def write(project: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return project


def pyproject(*dependencies: str, extra: str = "") -> str:
    deps = ", ".join(f'"{dep}"' for dep in dependencies)
    return f'[project]\nname = "srv"\nversion = "0.1.0"\ndependencies = [{deps}]\n{extra}'


class TestDetectProtocol:
    @pytest.mark.parametrize("dependency", ["arcade-mcp-server>=1.23", "arcade_mcp", "Arcade-MCP==1.16"])
    def test_arcade_mcp_means_arcade(self, tmp_path: Path, dependency: str) -> None:
        write(tmp_path, {"pyproject.toml": pyproject(dependency, "fastmcp")})

        assert detect_protocol(tmp_path) == "arcade"

    def test_anything_else_means_mcp(self, tmp_path: Path) -> None:
        write(tmp_path, {"requirements.txt": "fastmcp==3.4.1\n"})

        assert detect_protocol(tmp_path) == "mcp"

    def test_fastmcp_json_dependencies_are_read(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {"fastmcp.json": '{"environment": {"dependencies": ["arcade-mcp-server"]}}'},
        )

        assert detect_protocol(tmp_path) == "arcade"

    def test_a_project_with_no_dependency_source_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"server.py": "print('hi')\n"})

        with pytest.raises(ProjectCheckError, match="No dependency source"):
            detect_protocol(tmp_path)


class TestInstallSource:
    """The file the runner installs from, first that exists (DEP-537, DEP-390)."""

    def test_a_lock_wins(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {"pyproject.toml": pyproject(), "uv.lock": "", "requirements.txt": "", "fastmcp.json": "{}"},
        )

        assert install_source(tmp_path, "mcp") == "uv.lock"

    def test_fastmcp_json_comes_before_requirements_for_mcp_only(self, tmp_path: Path) -> None:
        write(tmp_path, {"requirements.txt": "", "fastmcp.json": "{}"})

        assert install_source(tmp_path, "mcp") == "fastmcp.json"
        assert install_source(tmp_path, "arcade") == "requirements.txt"

    def test_pyproject_last(self, tmp_path: Path) -> None:
        write(tmp_path, {"pyproject.toml": pyproject()})

        assert install_source(tmp_path, "mcp") == "pyproject.toml"


class TestRefusals:
    def test_a_poetry_project_without_a_lock_or_requirements_is_refused(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "pyproject.toml": (
                    '[tool.poetry]\nname = "srv"\n[tool.poetry.dependencies]\n'
                    'python = "^3.11"\nfastmcp = "^3.4"\n'
                )
            },
        )

        with pytest.raises(ProjectCheckError, match="poetry export"):
            check_project(tmp_path, protocol="mcp", runners=PY312)

    def test_a_poetry_project_with_requirements_deploys(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "pyproject.toml": '[tool.poetry.dependencies]\nfastmcp = "^3.4"\n',
                "requirements.txt": "fastmcp==3.4.1\n",
            },
        )

        assert check_project(tmp_path, protocol="mcp", runners=PY312) == []

    def test_requires_python_that_excludes_the_runner_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"pyproject.toml": pyproject(extra='requires-python = ">=3.13"\n')})

        with pytest.raises(ProjectCheckError, match=r"'>=3\.13'.*Python 3\.12"):
            check_project(tmp_path, protocol="mcp", runners=PY312)

    @pytest.mark.parametrize("specifier", [">=3.10", "~=3.12.1", ">=3.12,<3.13", "==3.12.*"])
    def test_requires_python_that_admits_the_runner_deploys(
        self, tmp_path: Path, specifier: str
    ) -> None:
        write(tmp_path, {"pyproject.toml": pyproject(extra=f'requires-python = "{specifier}"\n')})

        assert check_project(tmp_path, protocol="mcp", runners=PY312) == []

    def test_any_runner_that_admits_it_is_enough(self, tmp_path: Path) -> None:
        write(tmp_path, {"pyproject.toml": pyproject(extra='requires-python = ">=3.13"\n')})
        runners = [*PY312, DeploymentsRunner(language="python", version="3.13")]

        assert check_project(tmp_path, protocol="mcp", runners=runners) == []

    def test_no_runners_reported_skips_the_python_check(self, tmp_path: Path) -> None:
        write(tmp_path, {"pyproject.toml": pyproject(extra='requires-python = ">=3.99"\n')})

        assert check_project(tmp_path, protocol="mcp", runners=[]) == []


class TestWarnings:
    def test_unpinned_dependencies_are_named(self, tmp_path: Path) -> None:
        write(tmp_path, {"requirements.txt": "fastmcp>=3\nhttpx==0.28.1\nrich\n"})

        warnings = check_project(tmp_path, protocol="mcp", runners=PY312)

        assert len(warnings) == 1
        assert "fastmcp, rich" in warnings[0]
        assert "uv lock" in warnings[0]
        assert "pip freeze" in warnings[0]

    def test_a_lock_pins_everything(self, tmp_path: Path) -> None:
        write(tmp_path, {"pyproject.toml": pyproject("fastmcp>=3"), "uv.lock": ""})

        assert check_project(tmp_path, protocol="mcp", runners=PY312) == []

    def test_url_and_exact_pins_count_as_pinned(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "requirements.txt": (
                    "fastmcp===3.4.1\n"
                    "tool @ git+https://github.com/acme/tool@v1\n"
                    "wild==3.*\n"
                )
            },
        )

        warnings = check_project(tmp_path, protocol="mcp", runners=PY312)

        assert len(warnings) == 1
        assert "wild" in warnings[0]
        assert "fastmcp" not in warnings[0]

    def test_only_the_installed_source_is_checked(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {"pyproject.toml": pyproject("fastmcp>=3"), "requirements.txt": "fastmcp==3.4.1\n"},
        )

        assert check_project(tmp_path, protocol="mcp", runners=PY312) == []

    @pytest.mark.parametrize("protocol", ["arcade", "mcp"])
    def test_uv_sources_without_a_lock_warn_for_both_protocols(
        self, tmp_path: Path, protocol: str
    ) -> None:
        write(
            tmp_path,
            {
                "pyproject.toml": pyproject(
                    "turnkey-sdk==0.2.0",
                    extra='[tool.uv.sources]\nturnkey-sdk = { git = "https://github.com/tkhq/python-sdk" }\n',
                )
            },
        )

        warnings = check_project(tmp_path, protocol=protocol, runners=PY312)

        assert any("[tool.uv.sources]" in w and "uv lock" in w for w in warnings)

    def test_uv_sources_with_a_lock_are_fine(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "pyproject.toml": pyproject(
                    "turnkey-sdk==0.2.0", extra='[tool.uv.sources]\nturnkey-sdk = { path = "../sdk" }\n'
                ),
                "uv.lock": "",
            },
        )

        assert check_project(tmp_path, protocol="mcp", runners=PY312) == []

    def test_an_arcade_deploy_gets_only_the_uv_sources_warning(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {"pyproject.toml": pyproject("arcade-mcp-server>=1", extra='requires-python = ">=3.99"\n')},
        )

        assert check_project(tmp_path, protocol="arcade", runners=PY312) == []

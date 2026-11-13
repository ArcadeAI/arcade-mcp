"""Reading and checking the deploy config of an MCP server deploy."""

import json
from pathlib import Path

import pytest
from arcade_cli.deploy_config import (
    DeployConfigError,
    load_deploy_config,
    resolve_declared_values,
    runner_settings_json,
)


def write(project: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return project


PYPROJECT = """
[project]
name = "expense-tools"
version = "0.1.0"
dependencies = ["fastmcp"]
"""


class TestWhereItIsRead:
    def test_no_config_is_empty(self, tmp_path: Path) -> None:
        write(tmp_path, {"pyproject.toml": PYPROJECT})

        config = load_deploy_config(tmp_path)

        assert config.source is None
        assert config.command is None
        assert config.environment == {}
        assert config.secrets == []

    def test_pyproject_tool_arcade_deploy(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "pyproject.toml": PYPROJECT
                + '\n[tool.arcade.deploy]\ncommand = "python app.py"\nsecrets = ["OPENAI_API_KEY"]\n'
                + '[tool.arcade.deploy.environment]\nLOG_LEVEL = "info"\n',
            },
        )

        config = load_deploy_config(tmp_path)

        assert config.source == "pyproject.toml"
        assert config.command == "python app.py"
        assert config.secrets == ["OPENAI_API_KEY"]
        assert config.environment == {"LOG_LEVEL": "info"}

    def test_arcade_toml_for_a_requirements_only_project(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "requirements.txt": "fastmcp\n",
                "arcade.toml": '[deploy]\npath = "/api/mcp"\n',
            },
        )

        config = load_deploy_config(tmp_path)

        assert config.source == "arcade.toml"
        assert config.path == "/api/mcp"

    def test_arcade_toml_beside_a_pyproject_without_the_table(self, tmp_path: Path) -> None:
        write(tmp_path, {"pyproject.toml": PYPROJECT, "arcade.toml": '[deploy]\npath = "/x"\n'})

        assert load_deploy_config(tmp_path).source == "arcade.toml"

    def test_both_places_are_refused(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "pyproject.toml": PYPROJECT + '\n[tool.arcade.deploy]\npath = "/a"\n',
                "arcade.toml": '[deploy]\npath = "/b"\n',
            },
        )

        with pytest.raises(
            DeployConfigError, match=r"both .*\[tool\.arcade\.deploy\].*arcade\.toml"
        ):
            load_deploy_config(tmp_path)

    def test_an_arcade_toml_without_a_deploy_table_is_not_a_second_config(
        self, tmp_path: Path
    ) -> None:
        write(
            tmp_path,
            {
                "pyproject.toml": PYPROJECT + '\n[tool.arcade.deploy]\ncommand = "python app.py"\n',
                "arcade.toml": '[other]\nkey = "value"\n',
            },
        )

        config = load_deploy_config(tmp_path)

        assert config.source == "pyproject.toml"
        assert config.command == "python app.py"

    def test_an_arcade_toml_without_a_deploy_table_is_no_config(self, tmp_path: Path) -> None:
        write(tmp_path, {"requirements.txt": "fastmcp\n", "arcade.toml": '[other]\nkey = "v"\n'})

        assert load_deploy_config(tmp_path).source is None

    @pytest.mark.parametrize(
        ("name", "content"),
        [
            ("pyproject.toml", "[tool]\narcade = 1\n"),
            ("pyproject.toml", "tool = 1\n"),
            ("pyproject.toml", "[tool.arcade]\ndeploy = 1\n"),
            ("arcade.toml", "deploy = 1\n"),
        ],
    )
    def test_a_deploy_setting_that_isnt_a_table_is_refused_naming_it(
        self, tmp_path: Path, name: str, content: str
    ) -> None:
        write(tmp_path, {name: content})

        with pytest.raises(DeployConfigError, match=name.replace(".", r"\.")):
            load_deploy_config(tmp_path)

    def test_an_unreadable_file_is_refused_naming_it(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": "[deploy\n"})

        with pytest.raises(DeployConfigError, match="arcade.toml"):
            load_deploy_config(tmp_path)


class TestSettings:
    def test_api_key_and_oauth_client(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "arcade.toml": (
                    "[deploy]\n"
                    'api_key = { env = "API_KEY", header = "Authorization", scheme = "Bearer" }\n'
                    'oauth_client = { client_id = "abc", client_secret_env = "ENTRA_SECRET" }\n'
                ),
            },
        )

        config = load_deploy_config(tmp_path)

        assert config.api_key is not None
        assert (config.api_key.env, config.api_key.header, config.api_key.scheme) == (
            "API_KEY",
            "Authorization",
            "Bearer",
        )
        assert config.oauth_client is not None
        assert config.oauth_client.client_id == "abc"
        assert config.oauth_client.client_secret_env == "ENTRA_SECRET"

    def test_a_bare_key_header_has_no_scheme(self, tmp_path: Path) -> None:
        write(
            tmp_path, {"arcade.toml": '[deploy]\napi_key = { env = "K", header = "X-API-Key" }\n'}
        )

        api_key = load_deploy_config(tmp_path).api_key

        assert api_key is not None
        assert api_key.scheme is None

    def test_an_unknown_setting_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": "[deploy]\nport = 9000\n"})

        with pytest.raises(DeployConfigError, match="port"):
            load_deploy_config(tmp_path)

    def test_an_unknown_api_key_setting_lists_the_api_key_settings(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {"arcade.toml": '[deploy]\napi_key = { env = "K", header = "H", prefix = "x" }\n'},
        )

        with pytest.raises(DeployConfigError, match=r"api_key\.prefix .*env, header, scheme\)"):
            load_deploy_config(tmp_path)

    def test_a_non_string_environment_value_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": "[deploy.environment]\nRETRIES = 3\n"})

        with pytest.raises(DeployConfigError, match="RETRIES"):
            load_deploy_config(tmp_path)

    def test_a_path_must_start_with_a_slash(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": '[deploy]\npath = "api/mcp"\n'})

        with pytest.raises(DeployConfigError, match="must start with '/'"):
            load_deploy_config(tmp_path)

    def test_a_blank_command_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": '[deploy]\ncommand = " "\n'})

        with pytest.raises(DeployConfigError, match="`command` is empty"):
            load_deploy_config(tmp_path)


class TestNames:
    # Every name the deployment runner reserves, written out here so a change to the CLI's
    # copy shows up as a failing test.
    @pytest.mark.parametrize(
        "name",
        [
            "ARCADE_RUNNER_X",
            "KUBERNETES_SERVICE_HOST",
            "ARCADE_TELEMETRY_LOGS",
            "ARCADE_WORKER_SECRET",
            "ARCADE_ARTIFACT_STORE_URL",
            "ARCADE_BUNDLE_URL",
            "ARCADE_BUNDLE_KEY",
            "ARCADE_BUNDLE_DIR",
            "ARCADE_BUNDLE_NAME",
            "ARCADE_BUNDLE_ENTRYPOINT",
            "WORKER_PORT",
            "WORKER_PACKAGES",
            "WORKER_CACHE_ENABLED",
            "WORKER_CACHE_BUCKET",
            "WORKER_BUNDLE_BUCKET",
            "WORKER_BUNDLE_PATHS",
            "WORKER_API_CONFIG_ENABLED",
            "PATH",
            "HOME",
            "TMPDIR",
            "FASTMCP_HOME",
            "UV_PROJECT_ENVIRONMENT",
            "UV_CACHE_DIR",
            "UV_PYTHON_DOWNLOADS",
            "PIP_CACHE_DIR",
        ],
    )
    def test_a_name_the_runner_reserves_is_refused(self, tmp_path: Path, name: str) -> None:
        write(tmp_path, {"arcade.toml": f'[deploy]\nsecrets = ["{name}"]\n'})

        with pytest.raises(DeployConfigError, match=f"{name} is reserved"):
            load_deploy_config(tmp_path)

    def test_a_reserved_api_key_env_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": '[deploy]\napi_key = { env = "HOME", header = "X-Key" }\n'})

        with pytest.raises(DeployConfigError, match="HOME is reserved"):
            load_deploy_config(tmp_path)

    def test_a_reserved_environment_name_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": '[deploy.environment]\nPATH = "/bin"\n'})

        with pytest.raises(DeployConfigError, match="PATH is reserved"):
            load_deploy_config(tmp_path)

    @pytest.mark.parametrize(
        "name",
        [
            "ARCADE_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "AZURE_CLIENT_ID",
        ],
    )
    def test_other_arcade_and_cloud_names_are_allowed(self, tmp_path: Path, name: str) -> None:
        write(tmp_path, {"arcade.toml": f'[deploy]\nsecrets = ["{name}"]\n'})

        assert load_deploy_config(tmp_path).secrets == [name]

    def test_an_api_key_on_the_platform_credential_header_is_refused(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {"arcade.toml": '[deploy]\napi_key = { env = "K", header = "arcade-worker-auth" }\n'},
        )

        with pytest.raises(DeployConfigError, match="Arcade-Worker-Auth"):
            load_deploy_config(tmp_path)

    def test_a_name_declared_as_both_environment_and_secret_is_refused(
        self, tmp_path: Path
    ) -> None:
        write(
            tmp_path,
            {"arcade.toml": '[deploy]\nsecrets = ["TOKEN"]\n[deploy.environment]\nTOKEN = "x"\n'},
        )

        with pytest.raises(DeployConfigError, match="TOKEN"):
            load_deploy_config(tmp_path)

    def test_an_api_key_env_declared_as_an_environment_value_is_refused(
        self, tmp_path: Path
    ) -> None:
        # An environment value is shown in the server's details, and the runner puts its
        # own key in api_key.env unless a secret holds one.
        write(
            tmp_path,
            {
                "arcade.toml": (
                    '[deploy]\napi_key = { env = "API_KEY", header = "X-API-Key" }\n'
                    '[deploy.environment]\nAPI_KEY = "dev-key-123"\n'
                )
            },
        )

        with pytest.raises(DeployConfigError, match=r"API_KEY.*api_key\.env.*under `secrets`"):
            load_deploy_config(tmp_path)

    def test_an_api_key_in_pyproject_is_read(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "pyproject.toml": PYPROJECT
                + '\n[tool.arcade.deploy]\nsecrets = ["EXPENSE_API_KEY"]\n'
                'api_key = { env = "EXPENSE_API_KEY", header = "Authorization", scheme = "Bearer" }\n'
            },
        )

        config = load_deploy_config(tmp_path)

        assert config.source == "pyproject.toml"
        assert config.api_key is not None
        assert config.api_key.env == "EXPENSE_API_KEY"

    def test_an_invalid_variable_name_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": '[deploy]\nsecrets = ["MY-KEY"]\n'})

        with pytest.raises(DeployConfigError, match="MY-KEY"):
            load_deploy_config(tmp_path)


class TestDeclaredValues:
    def test_declared_secrets_come_from_the_environment(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "arcade.toml": (
                    '[deploy]\nsecrets = ["OPENAI_API_KEY"]\n'
                    'oauth_client = { client_id = "abc", client_secret_env = "ENTRA_SECRET" }\n'
                    '[deploy.environment]\nLOG_LEVEL = "info"\n'
                ),
            },
        )
        config = load_deploy_config(tmp_path)

        values = resolve_declared_values(
            config, {"OPENAI_API_KEY": "sk-1", "ENTRA_SECRET": "shh", "UNRELATED": "x"}
        )

        assert values.secrets == {"OPENAI_API_KEY": "sk-1"}
        assert values.environment == {"LOG_LEVEL": "info"}
        assert values.oauth_client == {"client_id": "abc", "client_secret": "shh"}

    def test_a_declared_secret_with_no_value_is_refused(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": '[deploy]\nsecrets = ["A", "B"]\n'})

        with pytest.raises(DeployConfigError, match=r"no value in your environment or \.env: B$"):
            resolve_declared_values(load_deploy_config(tmp_path), {"A": "1", "B": ""})

    def test_a_declared_key_secret_with_no_value_is_named_as_the_api_key(
        self, tmp_path: Path
    ) -> None:
        write(
            tmp_path,
            {
                "arcade.toml": (
                    '[deploy]\nsecrets = ["EXPENSE_API_KEY"]\n'
                    'api_key = { env = "EXPENSE_API_KEY", header = "X-API-Key" }\n'
                )
            },
        )

        with pytest.raises(DeployConfigError, match=r"EXPENSE_API_KEY \(api_key\.env\)"):
            resolve_declared_values(load_deploy_config(tmp_path), {})

    def test_an_oauth_client_secret_with_no_value_is_refused(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "arcade.toml": '[deploy]\noauth_client = { client_id = "abc", client_secret_env = "S" }\n'
            },
        )

        with pytest.raises(DeployConfigError, match="client_secret_env.*S"):
            resolve_declared_values(load_deploy_config(tmp_path), {})

    def test_no_oauth_client_sends_none(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": "[deploy]\n"})

        assert resolve_declared_values(load_deploy_config(tmp_path), {}).oauth_client is None


class TestRunnerSettings:
    def test_only_the_runners_share_is_written(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "arcade.toml": (
                    '[deploy]\npath = "/api/mcp"\nsecrets = ["K"]\n'
                    'api_key = { env = "K", header = "Authorization", scheme = "Bearer" }\n'
                    'oauth_client = { client_id = "abc", client_secret_env = "S" }\n'
                ),
            },
        )

        settings = json.loads(runner_settings_json(load_deploy_config(tmp_path)) or "")

        assert settings == {
            "api_key": {"env": "K", "header": "Authorization", "scheme": "Bearer"},
            "path": "/api/mcp",
        }

    def test_nothing_for_the_runner_writes_no_file(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": '[deploy]\ncommand = "python app.py"\n'})

        assert runner_settings_json(load_deploy_config(tmp_path)) is None


class TestNativeLibs:
    @pytest.mark.parametrize(
        "files",
        [
            {
                "pyproject.toml": PYPROJECT
                + '\n[tool.arcade.deploy]\nnative_libs = ["vendor/odbc"]\n'
            },
            {"arcade.toml": '[deploy]\nnative_libs = ["vendor/odbc"]\n'},
        ],
        ids=["pyproject.toml", "arcade.toml"],
    )
    def test_native_libs_alone_writes_the_runner_settings(
        self, tmp_path: Path, files: dict[str, str]
    ) -> None:
        write(tmp_path, {**files, "vendor/odbc/libmsodbcsql.so": ""})

        settings = json.loads(runner_settings_json(load_deploy_config(tmp_path)) or "")

        assert settings == {"native_libs": ["vendor/odbc"]}

    def test_entries_are_normalized(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            {
                "arcade.toml": '[deploy]\nnative_libs = ["./vendor/odbc/", "lib"]\n',
                "vendor/odbc/a.so": "",
                "lib/b.so": "",
            },
        )

        assert load_deploy_config(tmp_path).native_libs == ["vendor/odbc", "lib"]

    def test_no_native_libs_is_an_empty_list(self, tmp_path: Path) -> None:
        write(tmp_path, {"arcade.toml": "[deploy]\n"})

        assert load_deploy_config(tmp_path).native_libs == []

    @pytest.mark.parametrize(
        ("entry", "match"),
        [
            ("/opt/odbc", "not absolute paths"),
            ("C:/odbc", "not absolute paths"),
            ("../odbc", "leaves the project"),
            ("vendor/../../odbc", "leaves the project"),
            (".", "project directory itself"),
            ("", "empty entry"),
            ("vendor\\\\odbc", "use '/'"),
            (".libs", "leaves out"),
            ("vendor/__pycache__", "leaves out"),
            ("missing", "doesn't exist"),
            ("file.so", "isn't a directory"),
        ],
    )
    def test_an_entry_outside_the_project_or_missing_is_refused(
        self, tmp_path: Path, entry: str, match: str
    ) -> None:
        write(
            tmp_path,
            {
                "arcade.toml": f'[deploy]\nnative_libs = ["{entry}"]\n',
                "file.so": "",
                ".libs/a.so": "",
                "vendor/__pycache__/a.so": "",
            },
        )

        with pytest.raises(DeployConfigError, match=match):
            load_deploy_config(tmp_path)

    def test_a_symlink_out_of_the_project_is_refused(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside"
        outside.mkdir()
        project = write(tmp_path / "srv", {"arcade.toml": '[deploy]\nnative_libs = ["odbc"]\n'})
        try:
            (project / "odbc").symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("symlinks unavailable")

        with pytest.raises(DeployConfigError, match="leads outside the project"):
            load_deploy_config(project)

    @pytest.mark.parametrize("kind", ["file", "directory", "dangling"])
    def test_a_link_inside_an_entry_that_leads_outside_the_project_is_refused(
        self, tmp_path: Path, kind: str
    ) -> None:
        outside = write(tmp_path / "outside", {"libmsodbcsql.so.18": ""})
        project = write(
            tmp_path / "srv",
            {"arcade.toml": '[deploy]\nnative_libs = ["vendor/odbc"]\n', "vendor/odbc/ok.so": ""},
        )
        target = {
            "file": outside / "libmsodbcsql.so.18",
            "directory": outside,
            "dangling": project / "vendor" / "odbc" / "missing.so",
        }[kind]
        try:
            (project / "vendor" / "odbc" / "lib").symlink_to(
                target, target_is_directory=kind == "directory"
            )
        except OSError:
            pytest.skip("symlinks unavailable")

        with pytest.raises(
            DeployConfigError, match=r"vendor/odbc/lib in native_libs is a link outside"
        ):
            load_deploy_config(project)

    def test_a_link_to_a_library_in_the_project_is_allowed(self, tmp_path: Path) -> None:
        project = write(
            tmp_path,
            {
                "arcade.toml": '[deploy]\nnative_libs = ["vendor/odbc"]\n',
                "vendor/odbc/libodbc.so.2.0.0": "",
            },
        )
        try:
            (project / "vendor" / "odbc" / "libodbc.so.2").symlink_to("libodbc.so.2.0.0")
        except OSError:
            pytest.skip("symlinks unavailable")

        assert load_deploy_config(project).native_libs == ["vendor/odbc"]

    @pytest.mark.parametrize("where", ["inside", "entry", "parent"])
    def test_an_absolute_link_to_a_library_in_the_project_is_refused(
        self, tmp_path: Path, where: str
    ) -> None:
        # The bundle stores the link text, so an absolute target is broken on the runner.
        project = write(
            tmp_path,
            {
                "arcade.toml": '[deploy]\nnative_libs = ["vendor/odbc"]\n',
                "drivers/odbc/libodbc.so.2": "",
            },
        )
        links = {
            "inside": (project / "vendor/odbc/libodbc.so", project / "drivers/odbc/libodbc.so.2"),
            "entry": (project / "vendor/odbc", project / "drivers/odbc"),
            "parent": (project / "vendor", project / "drivers"),
        }
        link, target = links[where]
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target.resolve(), target_is_directory=target.is_dir())
        except OSError:
            pytest.skip("symlinks unavailable")

        with pytest.raises(DeployConfigError, match="absolute target"):
            load_deploy_config(project)

    def test_a_relative_link_for_the_entry_is_allowed(self, tmp_path: Path) -> None:
        project = write(
            tmp_path,
            {
                "arcade.toml": '[deploy]\nnative_libs = ["vendor/odbc"]\n',
                "drivers/odbc/libodbc.so.2": "",
            },
        )
        (project / "vendor").mkdir()
        try:
            (project / "vendor" / "odbc").symlink_to(
                # Path gives the OS's separator: Windows doesn't follow a relative link
                # written with forward slashes.
                Path("..", "drivers", "odbc"),
                target_is_directory=True,
            )
        except OSError:
            pytest.skip("symlinks unavailable")

        assert load_deploy_config(project).native_libs == ["vendor/odbc"]

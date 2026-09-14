import os
from pathlib import Path

import pytest
from arcade_cli.main import cli
from arcade_core.config_model import Config, NamedContext
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    os.environ["ARCADE_WORK_DIR"] = str(tmp_path)
    return tmp_path


def _seed_two_contexts() -> None:
    config = Config()
    config.contexts = {
        "cloud": NamedContext(kind="cloud", engine_url="https://api.arcade.dev"),
        "onprem": NamedContext(kind="self_hosted", engine_url="https://engine.acme.internal"),
    }
    config._apply_named_context("cloud", config.contexts["cloud"])
    config.save_to_file()


class TestContextCommands:
    def test_list_shows_all_contexts(self, work_dir: Path):
        _seed_two_contexts()

        result = runner.invoke(cli, ["context", "list"])

        assert result.exit_code == 0, result.output
        assert "cloud" in result.output
        assert "onprem" in result.output

    def test_use_switches_active_context(self, work_dir: Path):
        _seed_two_contexts()

        result = runner.invoke(cli, ["context", "use", "onprem"])

        assert result.exit_code == 0, result.output
        assert Config.load_from_file().active_context == "onprem"

    def test_use_unknown_context_exits_nonzero(self, work_dir: Path):
        _seed_two_contexts()

        result = runner.invoke(cli, ["context", "use", "nope"])

        assert result.exit_code != 0
        assert Config.load_from_file().active_context == "cloud"

    def test_show_active_context(self, work_dir: Path):
        _seed_two_contexts()

        result = runner.invoke(cli, ["context", "show"])

        assert result.exit_code == 0, result.output
        assert "cloud" in result.output
        assert "https://api.arcade.dev" in result.output

    def test_show_named_context(self, work_dir: Path):
        _seed_two_contexts()

        result = runner.invoke(cli, ["context", "show", "onprem"])

        assert result.exit_code == 0, result.output
        assert "https://engine.acme.internal" in result.output

    def test_show_missing_context_exits_nonzero(self, work_dir: Path):
        _seed_two_contexts()

        result = runner.invoke(cli, ["context", "show", "ghost"])

        assert result.exit_code != 0
        assert "ghost" in result.output

    def test_list_without_login_names_the_login_command(self, work_dir: Path):
        result = runner.invoke(cli, ["context", "list"])

        assert result.exit_code != 0
        assert "arcade login" in result.output

    def test_show_includes_user_and_project(self, work_dir: Path):
        from arcade_core.config_model import ContextConfig, UserConfig

        config = Config()
        config.contexts = {
            "onprem": NamedContext(
                kind="self_hosted",
                engine_url="https://engine.acme.internal",
                user=UserConfig(email="dev@acme.internal"),
                context=ContextConfig(
                    org_id="o", org_name="Acme", project_id="p", project_name="tools"
                ),
            )
        }
        config._apply_named_context("onprem", config.contexts["onprem"])
        config.save_to_file()

        result = runner.invoke(cli, ["context", "show"])

        assert result.exit_code == 0, result.output
        assert "dev@acme.internal" in result.output
        assert "Acme" in result.output
        assert "tools" in result.output

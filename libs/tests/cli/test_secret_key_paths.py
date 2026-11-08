"""Secret keys must never reach the API path as extra path segments (DEP-715, VDP F-1).

These tests use the real ``get_org_scoped_url`` so they cover the URL that is
actually sent, in both the logged-in (org/project) mode and the CI mode.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
import typer
from arcade_cli.context import ARCADE_API_KEY_ENV, ARCADE_URL_ENV
from arcade_cli.deploy import get_required_secrets, upsert_secrets_to_engine
from arcade_cli.secret import _upsert_secret, set_secret, state
from arcade_cli.utils import secret_url_path, validate_secret_key

ENGINE = "https://api.example.com"
NORMAL_PREFIX = f"{ENGINE}/v1/orgs/ORG/projects/PROJ"
CI_PREFIX = f"{ENGINE}/v1/admin"

MALICIOUS_KEYS = [
    "../../orgs/X/projects/Y/secrets/Z",
    "../../../v1/orgs/X/projects/Y/secrets/Z",
    "..",
    ".",
    "a/b",
    "%2e%2e",
    "..%2f..%2fZ",
    "KEY%2FOTHER",
    "KEY?x=1",
    "KEY#frag",
    "has space",
    "",
]


@pytest.fixture
def normal_mode():
    os.environ.pop(ARCADE_URL_ENV, None)
    os.environ.pop(ARCADE_API_KEY_ENV, None)
    config = SimpleNamespace(context=SimpleNamespace(org_id="ORG", project_id="PROJ"))
    with patch("arcade_cli.utils.validate_and_get_config", return_value=config):
        yield NORMAL_PREFIX


@pytest.fixture
def ci_mode(tmp_path: Path):
    os.environ["ARCADE_WORK_DIR"] = str(tmp_path)
    os.environ[ARCADE_URL_ENV] = ENGINE
    os.environ[ARCADE_API_KEY_ENV] = "ci-key"
    return CI_PREFIX


@pytest.fixture(params=["normal", "ci"])
def scoped_prefix(request):
    return request.getfixturevalue(f"{request.param}_mode")


class TestValidateSecretKey:
    @pytest.mark.parametrize("key", ["MY_SECRET_KEY", "lower_case", "KEY1", "_X", "1KEY"])
    def test_accepts_env_var_style_keys(self, key):
        assert validate_secret_key(key) == key

    @pytest.mark.parametrize("key", [*MALICIOUS_KEYS, "dash-key", "dot.key", "KEY\n"])
    def test_rejects_anything_else_with_a_clear_error(self, key):
        with pytest.raises(ValueError, match="letters, digits and underscores"):
            validate_secret_key(key)

    @pytest.mark.parametrize("key", MALICIOUS_KEYS)
    def test_path_builder_refuses_unsafe_keys(self, key):
        with pytest.raises(ValueError):
            secret_url_path(key)

    def test_path_builder_returns_single_segment(self):
        assert secret_url_path("MY_KEY") == "/secrets/MY_KEY"


class TestSecretSetUrl:
    def test_valid_key_targets_the_secret_path(self, scoped_prefix):
        state["engine_url"] = ENGINE
        with (
            patch("arcade_cli.secret.get_auth_headers", return_value={}),
            patch("arcade_cli.secret.httpx.put") as mock_put,
        ):
            _upsert_secret("MY_KEY", "value")

        url = mock_put.call_args.args[0]
        assert url == f"{scoped_prefix}/secrets/MY_KEY"
        # What httpx will actually send: no segment was collapsed.
        assert httpx.URL(url).path == httpx.URL(f"{scoped_prefix}/secrets/MY_KEY").path

    @pytest.mark.parametrize("key", MALICIOUS_KEYS)
    def test_unsafe_key_never_reaches_the_network(self, scoped_prefix, key):
        state["engine_url"] = ENGINE
        with (
            patch("arcade_cli.secret.get_auth_headers", return_value={}),
            patch("arcade_cli.secret.httpx.put") as mock_put,
            pytest.raises(ValueError),
        ):
            _upsert_secret(key, "value")
        mock_put.assert_not_called()

    def test_command_rejects_unsafe_key_pair(self):
        with (
            patch("arcade_cli.secret._upsert_secret") as mock_upsert,
            pytest.raises(typer.BadParameter, match="letters, digits and underscores"),
        ):
            set_secret(
                key_value_pairs=["../../orgs/X/projects/Y/secrets/Z=v"],
                from_env=False,
                env_file=".env",
            )
        mock_upsert.assert_not_called()

    def test_command_rejects_unsafe_env_file_key_before_any_upload(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("GOOD_KEY=one\n../EVIL=two\n")
        with (
            patch("arcade_cli.secret._upsert_secret") as mock_upsert,
            pytest.raises(typer.BadParameter, match=r"\.\./EVIL"),
        ):
            set_secret(key_value_pairs=None, from_env=True, env_file=str(env_file))
        mock_upsert.assert_not_called()


class TestDeploySecretUrl:
    def _upsert(self, keys: set[str]) -> MagicMock:
        client = MagicMock()
        client.put.return_value = MagicMock(raise_for_status=MagicMock())
        env = dict.fromkeys(keys, "secret-value")
        with (
            patch.dict(os.environ, env),
            patch("arcade_cli.deploy.get_auth_headers", return_value={}),
            patch("arcade_cli.deploy.httpx.Client", return_value=client),
        ):
            upsert_secrets_to_engine(ENGINE, keys)
        return client

    def test_valid_key_targets_the_secret_path(self, scoped_prefix):
        client = self._upsert({"MY_KEY"})
        client.put.assert_called_once()
        assert client.put.call_args.args[0] == f"{scoped_prefix}/secrets/MY_KEY"

    def test_unsafe_key_is_skipped_and_others_still_upload(self, scoped_prefix, capsys):
        client = self._upsert({"GOOD_KEY", "../EVIL"})
        urls = [c.args[0] for c in client.put.call_args_list]
        assert urls == [f"{scoped_prefix}/secrets/GOOD_KEY"]
        assert "letters, digits and underscores" in capsys.readouterr().out

    def test_tool_requirement_with_unsafe_key_fails_validation(self):
        tools = [
            {"requirements": {"secrets": [{"key": "OK_KEY"}]}},
            {"requirements": {"secrets": [{"key": "../../orgs/X/projects/Y/secrets/Z"}]}},
        ]
        response = MagicMock(json=MagicMock(return_value=tools))
        with (
            patch("arcade_cli.deploy.httpx.get", return_value=response),
            pytest.raises(ValueError, match="letters, digits and underscores"),
        ):
            get_required_secrets("http://127.0.0.1:1", "srv", "1.0.0")

    def test_tool_requirement_with_valid_keys_passes(self):
        tools = [{"requirements": {"secrets": [{"key": "OK_KEY"}, {"key": "other_key"}]}}]
        response = MagicMock(json=MagicMock(return_value=tools))
        with patch("arcade_cli.deploy.httpx.get", return_value=response):
            assert get_required_secrets("http://127.0.0.1:1", "srv", "1.0.0") == {
                "OK_KEY",
                "other_key",
            }

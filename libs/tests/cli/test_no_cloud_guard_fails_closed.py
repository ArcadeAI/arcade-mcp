"""An unreadable context must not quietly switch the no-Cloud guard off.

The guard's own message promises that requests stay inside the operator's
environment. A credentials file it cannot parse is the case where it does not
know whether that promise applies, which is the wrong moment to assume it does.
"""

import pytest
from arcade_cli.context import NoCloudGuardError, guard_no_cloud


@pytest.fixture
def unreadable_context(tmp_path, monkeypatch):
    bad = tmp_path / "credentials.yaml"
    bad.write_text("cloud:\n  contexts: [this is not a mapping\n")
    monkeypatch.setattr(
        "arcade_core.config_model.Config.get_config_file_path", classmethod(lambda cls: bad)
    )
    monkeypatch.delenv("ARCADE_URL", raising=False)
    monkeypatch.delenv("ARCADE_API_KEY", raising=False)
    return bad


@pytest.fixture
def no_context(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "arcade_core.config_model.Config.get_config_file_path",
        classmethod(lambda cls: tmp_path / "nothing.yaml"),
    )
    monkeypatch.delenv("ARCADE_URL", raising=False)
    monkeypatch.delenv("ARCADE_API_KEY", raising=False)


class TestAnUnreadableContext:
    def test_a_cloud_host_is_refused(self, unreadable_context):
        with pytest.raises(NoCloudGuardError) as excinfo:
            guard_no_cloud("https://api.arcade.dev")
        assert "could not be read" in str(excinfo.value)

    def test_the_message_says_how_to_recover(self, unreadable_context):
        with pytest.raises(NoCloudGuardError) as excinfo:
            guard_no_cloud("https://cloud.arcade.dev")
        assert "arcade logout" in str(excinfo.value)

    def test_a_self_hosted_host_is_left_alone(self, unreadable_context):
        guard_no_cloud("https://engine.internal.example")


class TestNoContextAtAll:
    def test_a_first_login_against_cloud_is_allowed(self, no_context):
        guard_no_cloud("https://cloud.arcade.dev")

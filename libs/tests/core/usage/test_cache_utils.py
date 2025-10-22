import pytest
from arcade_core.usage import is_tracking_enabled


@pytest.mark.parametrize(
    "env_value, expected",
    [
        pytest.param("1", True, id="enabled_with_1"),
        pytest.param("true", True, id="enabled_with_true_lowercase"),
        pytest.param("TRUE", True, id="enabled_with_true_uppercase"),
        pytest.param("True", True, id="enabled_with_true_titlecase"),
        pytest.param("yes", True, id="enabled_with_yes_lowercase"),
        pytest.param("YES", True, id="enabled_with_yes_uppercase"),
        pytest.param("Yes", True, id="enabled_with_yes_titlecase"),
        pytest.param("on", True, id="enabled_with_on_lowercase"),
        pytest.param("ON", True, id="enabled_with_on_uppercase"),
        pytest.param("On", True, id="enabled_with_on_titlecase"),
        pytest.param("anything_else", True, id="enabled_with_random_string"),
        pytest.param("0", False, id="disabled_with_0"),
        pytest.param("false", False, id="disabled_with_false_lowercase"),
        pytest.param("FALSE", False, id="disabled_with_false_uppercase"),
        pytest.param("False", False, id="disabled_with_false_titlecase"),
        pytest.param("no", False, id="disabled_with_no_lowercase"),
        pytest.param("NO", False, id="disabled_with_no_uppercase"),
        pytest.param("No", False, id="disabled_with_no_titlecase"),
        pytest.param("off", False, id="disabled_with_off_lowercase"),
        pytest.param("OFF", False, id="disabled_with_off_uppercase"),
        pytest.param("Off", False, id="disabled_with_off_titlecase"),
    ],
)
def test_is_tracking_enabled_with_env_var(
    monkeypatch: pytest.MonkeyPatch, env_value: str, expected: bool
) -> None:
    """Test is_tracking_enabled() with various environment variable values."""
    monkeypatch.setenv("ARCADE_USAGE_TRACKING", env_value)
    assert is_tracking_enabled() == expected


def test_is_tracking_enabled_default_when_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test is_tracking_enabled() returns True when environment variable is not set."""
    monkeypatch.delenv("ARCADE_USAGE_TRACKING", raising=False)
    assert is_tracking_enabled() is True


def test_is_tracking_enabled_default_when_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test is_tracking_enabled() returns True when environment variable is empty string."""
    monkeypatch.setenv("ARCADE_USAGE_TRACKING", "")
    assert is_tracking_enabled() is True

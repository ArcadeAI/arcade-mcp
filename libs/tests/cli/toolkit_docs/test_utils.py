from types import ModuleType
from unittest.mock import MagicMock

from arcade_cli.toolkit_docs.utils import (
    clean_fully_qualified_name,
    get_toolkit_auth_type,
    is_well_known_provider,
)
from arcade_core.auth import Asana, AuthProviderType, Google, OAuth2, Slack
from arcade_core.schema import ToolAuthRequirement


def test_get_toolkit_auth_type_none():
    assert get_toolkit_auth_type(requirement=None) == ""


def test_get_toolkit_auth_type_with_provider_type():
    requirement = ToolAuthRequirement(provider_type=AuthProviderType.oauth2.value)
    assert get_toolkit_auth_type(requirement=requirement) == 'authType="OAuth2"'

    requirement = ToolAuthRequirement(provider_type="another_type")
    assert get_toolkit_auth_type(requirement=requirement) == 'authType="another_type"'

    requirement = ToolAuthRequirement(provider_type="")
    assert get_toolkit_auth_type(requirement=requirement) == ""


def test_is_well_known_provider_none():
    assert not is_well_known_provider(provider_id=None, auth_module=MagicMock(spec=ModuleType))


def test_is_well_known_provider_matching_provider_id():
    mock_auth_module = MagicMock(spec=ModuleType)

    mock_auth_module.OAuth2 = OAuth2
    mock_auth_module.Google = Google
    mock_auth_module.Slack = Slack

    assert is_well_known_provider(provider_id=Google().provider_id, auth_module=mock_auth_module)
    assert is_well_known_provider(provider_id=Slack().provider_id, auth_module=mock_auth_module)
    assert not is_well_known_provider(provider_id=Asana().provider_id, auth_module=mock_auth_module)
    assert not is_well_known_provider(provider_id="another_provider", auth_module=mock_auth_module)


def test_clean_fully_qualified_name():
    assert clean_fully_qualified_name("Outlook.ListEmails") == "Outlook.ListEmails"
    assert clean_fully_qualified_name("Outlook.ListEmails@1.0.0") == "Outlook.ListEmails"

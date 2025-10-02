from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.toolkit_docs.utils import (
    clean_fully_qualified_name,
    get_toolkit_auth_type,
    is_well_known_provider,
    pascal_to_snake_case,
    read_toolkit_metadata,
)
from arcade_core.auth import Asana, AuthProviderType, Google, OAuth2, Slack
from arcade_core.schema import ToolAuthRequirement


@patch("arcade_cli.toolkit_docs.utils.open")
@patch("arcade_cli.toolkit_docs.utils.tomllib")
def test_read_toolkit_metadata(mock_tomllib, mock_open):
    from unittest.mock import MagicMock, mock_open as mock_open_func

    sample_pyproject_toml = """
[build-system]
requires = [ "hatchling",]
build-backend = "hatchling.build"

[project]
name = "arcade_jira"
version = "0.1.2"
description = "Arcade.dev LLM tools for interacting with Atlassian Jira"
requires-python = ">=3.10"
dependencies = [
    "arcade-tdk>=2.0.0,<3.0.0",
    "httpx>=0.27.2,<1.0.0",
]
[[project.authors]]
name = "Arcade"
email = "dev@arcade.dev"

[project.optional-dependencies]
dev = [
    "arcade-mcp[evals]>=2.0.0,<3.0.0",
    "arcade-serve>=2.0.0,<3.0.0",
    "pytest>=8.3.0,<8.4.0",
    "pytest-cov>=4.0.0,<4.1.0",
    "pytest-asyncio>=0.24.0,<0.25.0",
    "pytest-mock>=3.11.1,<3.12.0",
    "mypy>=1.5.1,<1.6.0",
    "pre-commit>=3.4.0,<3.5.0",
    "tox>=4.11.1,<4.12.0",
    "ruff>=0.7.4,<0.8.0",
]

# Use local path sources for arcade libs when working locally
[tool.uv.sources]
arcade-mcp = {path = "../../", editable = true}
arcade-tdk = { path = "../../libs/arcade-tdk/", editable = true }
arcade-serve = { path = "../../libs/arcade-serve/", editable = true }

[tool.mypy]
files = [ "arcade_jira/**/*.py",]
python_version = "3.10"
disallow_untyped_defs = "True"
disallow_any_unimported = "True"
no_implicit_optional = "True"
check_untyped_defs = "True"
warn_return_any = "True"
warn_unused_ignores = "True"
show_error_codes = "True"
ignore_missing_imports = "True"

[tool.pytest.ini_options]
testpaths = [ "tests",]

[tool.coverage.report]
skip_empty = true

[tool.hatch.build.targets.wheel]
packages = [ "arcade_jira",]
    """

    # Setup mock to handle both binary and text mode
    def open_side_effect(path, mode="r"):
        if mode == "rb":
            return mock_open_func(read_data=sample_pyproject_toml.encode()).return_value
        else:
            return mock_open_func(read_data=sample_pyproject_toml).return_value

    mock_open.side_effect = open_side_effect
    mock_tomllib.load.return_value = {"project": {"name": "arcade_jira"}}

    assert read_toolkit_metadata("path/to/toolkits/jira") == "arcade_jira"


@patch("arcade_cli.toolkit_docs.utils.open")
@patch("arcade_cli.toolkit_docs.utils.tomllib")
def test_read_toolkit_metadata_missing_project_name(mock_tomllib, mock_open):
    from unittest.mock import mock_open as mock_open_func

    sample_pyproject_toml = """
[build-system]
requires = [ "hatchling",]
build-backend = "hatchling.build"

[project]
version = "0.1.2"
description = "Arcade.dev LLM tools for interacting with Atlassian Jira"
requires-python = ">=3.10"
dependencies = [
    "arcade-tdk>=2.0.0,<3.0.0",
    "httpx>=0.27.2,<1.0.0",
]
[[project.authors]]
name = "Arcade"
email = "dev@arcade.dev"
    """

    # Setup mock to handle both binary and text mode
    def open_side_effect(path, mode="r"):
        if mode == "rb":
            return mock_open_func(read_data=sample_pyproject_toml.encode()).return_value
        else:
            return mock_open_func(read_data=sample_pyproject_toml).return_value

    mock_open.side_effect = open_side_effect
    mock_tomllib.load.return_value = {"project": {}}  # Missing "name"

    with pytest.raises(ValueError):
        read_toolkit_metadata("path/to/toolkits/jira")


def test_pascal_to_snake_case():
    assert pascal_to_snake_case("PascalCase") == "pascal_case"
    assert pascal_to_snake_case("PascalCase_abc") == "pascal_case_abc"


def test_get_toolkit_auth_type_none():
    from arcade_core.schema import ToolRequirements

    tool_req = ToolRequirements()
    assert get_toolkit_auth_type(tool_req=tool_req) == 'authType="None"'


def test_get_toolkit_auth_type_with_provider_type():
    from arcade_core.schema import ToolRequirements, ToolSecretRequirement

    tool_req = ToolRequirements(authorization=ToolAuthRequirement(provider_type=AuthProviderType.oauth2.value))
    assert get_toolkit_auth_type(tool_req=tool_req) == 'authType="OAuth2"'

    tool_req = ToolRequirements(authorization=ToolAuthRequirement(provider_type="another_type"))
    assert get_toolkit_auth_type(tool_req=tool_req) == 'authType="another_type"'

    tool_req = ToolRequirements(secrets=[ToolSecretRequirement(key="API_KEY")])
    assert get_toolkit_auth_type(tool_req=tool_req) == 'authType="API Key"'


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

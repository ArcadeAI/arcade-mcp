from unittest.mock import MagicMock, patch

import pytest
from arcade.sdk.errors import ToolExecutionError

from arcade_code_sandbox.tools.e2b import create_static_matplotlib_chart, run_code
from arcade_code_sandbox.tools.models import E2BSupportedLanguage


@pytest.fixture
def mock_sandbox():
    with patch("arcade_code_sandbox.tools.e2b.Sandbox") as mock:
        yield mock.return_value.__enter__.return_value


def test_run_code_success(mock_sandbox):
    mock_execution = MagicMock()
    mock_execution.to_json.return_value = '{"result": "success"}'
    mock_sandbox.run_code.return_value = mock_execution

    result = run_code("print('Hello, World!')", E2BSupportedLanguage.PYTHON)
    assert result == '{"result": "success"}'


def test_run_code_error(mock_sandbox):
    mock_execution = MagicMock()
    mock_execution.to_json.side_effect = ToolExecutionError("Execution failed")
    mock_sandbox.run_code.return_value = mock_execution

    with pytest.raises(ToolExecutionError, match="Execution failed"):
        run_code("print('Hello, World!')", E2BSupportedLanguage.PYTHON)


def test_create_static_matplotlib_chart_success(mock_sandbox):
    mock_execution = MagicMock()
    mock_execution.results = [MagicMock(png="base64encodedimage")]
    mock_execution.logs.to_json.return_value = '{"logs": "log data"}'
    mock_execution.error = None
    mock_sandbox.run_code.return_value = mock_execution

    result = create_static_matplotlib_chart("import matplotlib.pyplot as plt")
    assert result == {
        "base64_image": "base64encodedimage",
        "logs": '{"logs": "log data"}',
        "error": None,
    }


def test_create_static_matplotlib_chart_error(mock_sandbox):
    mock_execution = MagicMock()
    mock_execution.results = []
    mock_execution.logs.to_json.return_value = '{"logs": "log data"}'
    mock_execution.error.to_json.return_value = '{"error": "some error"}'
    mock_sandbox.run_code.return_value = mock_execution

    result = create_static_matplotlib_chart("import matplotlib.pyplot as plt")
    assert result == {
        "base64_image": None,
        "logs": '{"logs": "log data"}',
        "error": '{"error": "some error"}',
    }

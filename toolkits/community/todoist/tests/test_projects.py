from unittest.mock import MagicMock

import pytest
from arcade_todoist.tools.projects import get_projects

from tests.fakes import PROJECTS_API_RESPONSE, PROJECTS_PARSED_RESPONSE


@pytest.mark.asyncio
async def test_get_projects_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = PROJECTS_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await get_projects(context=tool_context)

    assert result == PROJECTS_PARSED_RESPONSE

    httpx_mock.get.assert_called_once()

import pytest

from {{ package_name }}.tools.sample import say_hello


@pytest.mark.asyncio
async def test_hello(mock_context) -> None:
    result = await say_hello(mock_context, "developer")
    assert result == "Hello, developer!"

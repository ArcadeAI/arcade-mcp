from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from arcade_mcp_server import Context

from arcade_perplexity.tools.search import (
    PERPLEXITY_SEARCH_URL,
    SearchRecencyFilter,
    search,
)


@pytest.fixture
def mock_context() -> Context:
    context = MagicMock(spec=Context)
    context.get_secret = MagicMock(return_value="test-api-key")
    return context


def _make_async_client_patch(json_payload: dict | None = None, status_code: int = 200):
    """Patch httpx.AsyncClient so that .post returns a configured response.

    Returns a tuple of (patcher, post_mock) so tests can inspect the call.
    """
    json_payload = json_payload if json_payload is not None else {"results": []}

    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json = MagicMock(return_value=json_payload)
    response.raise_for_status = MagicMock()

    post_mock = AsyncMock(return_value=response)

    async_client = MagicMock()
    async_client.post = post_mock
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=None)

    patcher = patch(
        "arcade_perplexity.tools.search.httpx.AsyncClient",
        return_value=async_client,
    )
    return patcher, post_mock


@pytest.mark.asyncio
async def test_search_happy_path_returns_normalized_results(mock_context: Context) -> None:
    api_payload = {
        "results": [
            {
                "title": "Result One",
                "url": "https://example.com/one",
                "snippet": "First snippet",
                "date": "2026-01-01",
            },
            {
                "title": "Result Two",
                "url": "https://example.com/two",
                "snippet": "Second snippet",
            },
        ],
        "id": "abc",
    }
    patcher, post_mock = _make_async_client_patch(json_payload=api_payload)
    with patcher:
        results = await search(mock_context, query="who is ada lovelace?")

    assert results == [
        {
            "title": "Result One",
            "url": "https://example.com/one",
            "snippet": "First snippet",
        },
        {
            "title": "Result Two",
            "url": "https://example.com/two",
            "snippet": "Second snippet",
        },
    ]

    post_mock.assert_awaited_once()
    call_args = post_mock.await_args
    assert call_args.args[0] == PERPLEXITY_SEARCH_URL
    body = call_args.kwargs["json"]
    assert body["query"] == "who is ada lovelace?"
    assert body["max_results"] == 5
    assert "search_recency_filter" not in body


@pytest.mark.asyncio
async def test_search_sends_required_auth_and_attribution_headers(
    mock_context: Context,
) -> None:
    patcher, post_mock = _make_async_client_patch()
    with patcher:
        await search(mock_context, query="test")

    headers = post_mock.await_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-api-key"
    assert headers["Content-Type"] == "application/json"
    assert "X-Pplx-Integration" in headers
    integration = headers["X-Pplx-Integration"]
    assert integration.startswith("arcade/")
    # ensure slug is exactly "arcade" (not e.g. "arcade-ai" or "arcade-mcp")
    assert integration.split("/", 1)[0] == "arcade"


@pytest.mark.asyncio
async def test_search_clamps_max_results_to_upper_bound(mock_context: Context) -> None:
    patcher, post_mock = _make_async_client_patch()
    with patcher:
        await search(mock_context, query="test", max_results=999)

    assert post_mock.await_args.kwargs["json"]["max_results"] == 20


@pytest.mark.asyncio
async def test_search_passes_recency_filter(mock_context: Context) -> None:
    patcher, post_mock = _make_async_client_patch()
    with patcher:
        await search(
            mock_context,
            query="latest news",
            search_recency_filter=SearchRecencyFilter.WEEK,
        )

    body = post_mock.await_args.kwargs["json"]
    assert body["search_recency_filter"] == "week"


@pytest.mark.asyncio
async def test_search_raises_on_http_error(mock_context: Context) -> None:
    request = httpx.Request("POST", PERPLEXITY_SEARCH_URL)
    response = httpx.Response(status_code=401, request=request)
    error = httpx.HTTPStatusError("unauthorized", request=request, response=response)

    bad_response = MagicMock(spec=httpx.Response)
    bad_response.status_code = 401
    bad_response.raise_for_status = MagicMock(side_effect=error)
    bad_response.json = MagicMock(return_value={})

    post_mock = AsyncMock(return_value=bad_response)
    async_client = MagicMock()
    async_client.post = post_mock
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "arcade_perplexity.tools.search.httpx.AsyncClient",
            return_value=async_client,
        ),
        pytest.raises(Exception),  # noqa: B017
    ):
        await search(mock_context, query="test")

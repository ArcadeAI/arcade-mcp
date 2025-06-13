import pytest
import serpapi
from arcade_tdk.errors import ToolExecutionError

from arcade_search.utils import call_serpapi, prepare_params


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "engine, kwargs, expected",
    [
        ("google", {}, {"engine": "google"}),
        (
            "google",
            {"q": "test", "window": 10, "time": "00:12:12"},
            {
                "engine": "google",
                "q": "test",
                "window": 10,
                "time": "00:12:12",
            },
        ),
    ],
)
async def test_prepare_params(engine, kwargs, expected):
    params = prepare_params(engine, **kwargs)
    assert params == expected


@pytest.mark.parametrize(
    "error_message, sanitized_message",
    [
        (
            "You hit your rate limit",
            "You hit your rate limit",
        ),
        (
            "Bad Request for url: https://serpapi.com/search?engine=google_hotels&api_key=ABC123456",
            "Bad Request for url: https://serpapi.com/search?engine=google_hotels&api_key=***",
        ),
        (
            "Bad Request for url: https://serpapi.com/search?engine=google_hotels&api_key=ABC123456 make sure the api key is correct",
            "Bad Request for url: https://serpapi.com/search?engine=google_hotels&api_key=*** make sure the api key is correct",
        ),
    ],
)
def test_call_serpapi_failure(monkeypatch, dummy_context, error_message, sanitized_message):
    def fake_serpapi_search(self, params: dict) -> dict:
        raise Exception(error_message)  # noqa: TRY002

    monkeypatch.setattr(serpapi.Client, "search", fake_serpapi_search)

    with pytest.raises(ToolExecutionError) as excinfo:
        call_serpapi(dummy_context, {})

    assert excinfo.value.developer_message == sanitized_message

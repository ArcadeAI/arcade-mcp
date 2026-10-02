"""Unit tests that run the real tool functions against a mocked Darkmoon Dashboard API."""

import json
from typing import Any

import httpx
import pytest
from arcade_mcp_server.exceptions import ToolExecutionError, UpstreamError

from darkmoon.tools import tools_pentest
from darkmoon.tools.tools_pentest import (
    get_findings,
    get_run_status,
    list_campaigns,
    list_pull_requests,
    run_pentest,
)

BASE = "https://darkmoon.test"
_REAL_CLIENT = httpx.AsyncClient


class FakeContext:
    def __init__(self) -> None:
        self._secrets = {
            "DARKMOON_BASE_URL": BASE + "/",
            "DARKMOON_USERNAME": "analyst",
            "DARKMOON_PASSWORD": "s3cret",
        }

    def get_secret(self, key: str) -> str:
        return self._secrets[key]


def install_api(monkeypatch, routes: dict[tuple[str, str], Any], seen: list | None = None):
    """Route every httpx.AsyncClient through a MockTransport serving `routes`."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        key = (request.method, request.url.path)
        if key == ("POST", "/api/v1/auth/login"):
            body = json.loads(request.content)
            if body["password"] != "s3cret":
                return httpx.Response(401, json={"detail": "bad credentials"})
            return httpx.Response(200, json={"token": "jwt-token"})
        assert request.headers.get("authorization") == "Bearer jwt-token"
        if key not in routes:
            return httpx.Response(404, json={"detail": "not found"})
        status, body = routes[key]
        return httpx.Response(status, json=body)

    real = _REAL_CLIENT

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(tools_pentest.httpx, "AsyncClient", factory)


async def test_run_pentest_sends_payload(monkeypatch):
    seen: list[httpx.Request] = []
    install_api(monkeypatch, {("POST", "/api/v1/run/campaign"): (200, {"run_id": "run_1"})}, seen)
    result = await run_pentest(
        FakeContext(), " app.example.com ", program="acme", focus=["auth", " "], severity="high"
    )
    assert result == {"status": "started", "run_id": "run_1", "target": "app.example.com"}
    sent = json.loads(seen[-1].content)
    assert sent == {
        "target": "app.example.com",
        "program": "acme",
        "focus": ["auth"],
        "severity": "high",
    }


async def test_run_pentest_requires_target(monkeypatch):
    install_api(monkeypatch, {})
    with pytest.raises(ToolExecutionError, match="target is required"):
        await run_pentest(FakeContext(), "  ")


async def test_get_run_status_states(monkeypatch):
    url = ("GET", "/api/v1/run/logs/run_1")
    install_api(monkeypatch, {url: (200, {"data": [{"type": "run_started"}], "total": 1})})
    assert (await get_run_status(FakeContext(), "run_1"))["status"] == "running"

    install_api(
        monkeypatch,
        {url: (200, {"data": [{"type": "run_started"}, {"type": "run_completed"}]})},
    )
    done = await get_run_status(FakeContext(), "run_1")
    assert done["status"] == "completed" and done["event_count"] == 2

    install_api(monkeypatch, {url: (200, {"data": [{"type": "run_error"}]})})
    assert (await get_run_status(FakeContext(), "run_1"))["status"] == "error"

    install_api(monkeypatch, {})
    assert (await get_run_status(FakeContext(), "run_1"))["status"] == "unknown"


async def test_list_campaigns(monkeypatch):
    campaigns = [{"id": "camp_1", "status": "completed"}]
    install_api(monkeypatch, {("GET", "/api/v1/campaigns"): (200, {"data": campaigns, "total": 1})})
    assert await list_campaigns(FakeContext()) == {"total": 1, "campaigns": campaigns}


async def test_get_findings(monkeypatch):
    seen: list[httpx.Request] = []
    finding = {"title": "SQL injection", "severity": "high", "status": "exploited"}
    install_api(
        monkeypatch,
        {
            ("GET", "/api/v1/vulnerabilities"): (
                200,
                {"data": [finding], "total": 1, "stats": {"high": 1}},
            )
        },
        seen,
    )
    result = await get_findings(FakeContext(), "camp_1")
    assert result == {
        "campaign_id": "camp_1",
        "total": 1,
        "stats": {"high": 1},
        "findings": [finding],
    }
    assert seen[-1].url.params["campaign_id"] == "camp_1"


async def test_list_pull_requests_filters_by_state(monkeypatch):
    prs = [{"id": "1", "state": "open"}, {"id": "2", "state": "merged"}]
    install_api(monkeypatch, {("GET", "/api/v1/pull-requests"): (200, {"data": prs})})
    result = await list_pull_requests(FakeContext(), state="OPEN")
    assert result == {"total": 1, "pull_requests": [prs[0]]}
    with pytest.raises(ToolExecutionError, match="state must be one of"):
        await list_pull_requests(FakeContext(), state="bogus")


async def test_bad_credentials_surface_a_clear_error(monkeypatch):
    install_api(monkeypatch, {})
    ctx = FakeContext()
    ctx._secrets["DARKMOON_PASSWORD"] = "wrong"
    with pytest.raises(UpstreamError, match="authentication failed") as exc:
        await list_campaigns(ctx)
    assert "wrong" not in str(exc.value)


async def test_api_error_detail_is_reported(monkeypatch):
    install_api(monkeypatch, {("GET", "/api/v1/campaigns"): (500, {"detail": "db down"})})
    with pytest.raises(UpstreamError, match="db down"):
        await list_campaigns(FakeContext())

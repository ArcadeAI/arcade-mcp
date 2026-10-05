"""Supporting transport regressions; public gateway scenarios remain primary proof."""

from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
import pytest
from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

VERSION = "2026-07-28"
HEADERS = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": VERSION}


@pytest.fixture
def elicitation_client():
    application = MCPApp(name="Inputs", auth_disabled=True)
    invocations = []

    @application.tool
    async def ask(
        context: Context,
        mode: Annotated[str, "form or url"],
        elicitation_id: Annotated[str | None, "Optional legacy identifier"] = "approval",
    ) -> Annotated[dict[str, Any], "The submitted answer"]:
        """Request a single answer."""
        invocations.append(mode)
        if mode == "url":
            response = await context.ui.elicit(
                "Approve",
                mode="url",
                url="https://example.com/approval",
                elicitation_id=elicitation_id,
            )
        else:
            response = await context.ui.elicit(
                "Confirm", schema={"type": "object", "properties": {"value": {"type": "string"}}}
            )
        return response.model_dump(exclude_none=True)

    @application.tool
    async def twice(context: Context) -> Annotated[dict[str, Any], "Both answers"]:
        """Request two successive inputs."""
        first = await context.ui.elicit("First")
        second = await context.ui.elicit(
            "Second", mode="url", url="https://example.com/second", elicitation_id="second"
        )
        return {
            "first": first.model_dump(exclude_none=True),
            "second": second.model_dump(exclude_none=True),
        }

    @asynccontextmanager
    async def open_client(json_response=True):
        server = MCPServer(catalog=application._catalog, auth_disabled=True)
        await server.start()
        manager = HTTPSessionManager(server=server, json_response=json_response, stateless=False)

        async def endpoint(scope: Scope, receive: Receive, send: Send) -> None:
            await manager.handle_request(scope, receive, send)

        app = Starlette(routes=[Mount("/mcp", app=endpoint)])
        try:
            async with (
                manager.run(),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://server"
                ) as client,
            ):
                yield client, invocations
        finally:
            await server.stop()

    return open_client


async def call(client, name="Inputs_Ask", arguments=None, capabilities=None, **continuation):
    response = await client.post(
        "/mcp/",
        headers=HEADERS,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {},
                **continuation,
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": VERSION,
                    "io.modelcontextprotocol/clientCapabilities": capabilities or {},
                    "io.modelcontextprotocol/clientInfo": {"name": "proof", "version": "1"},
                },
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,identifier", [("form", "approval"), ("url", "approval"), ("url", None)]
)
@pytest.mark.parametrize("action", ["accept", "decline", "cancel"])
async def test_prompt_and_response_without_session(elicitation_client, mode, identifier, action):
    async with elicitation_client() as (client, invocations):
        args = {"mode": mode, "elicitation_id": identifier}
        first = await call(client, arguments=args, capabilities={"elicitation": {mode: {}}})
        result = first["result"]
        assert result["resultType"] == "input_required", (
            f"modern input request not delivered: {first}"
        )
        key, request = next(iter(result["inputRequests"].items()))
        assert request["method"] == "elicitation/create"
        if mode == "form":
            assert "mode" not in request["params"]
            assert request["params"]["requestedSchema"]["properties"] == {
                "value": {"type": "string"}
            }
        else:
            assert request["params"]["url"] == "https://example.com/approval"
            if identifier is None:
                assert "elicitationId" not in request["params"]
            else:
                assert request["params"]["elicitationId"] == identifier
        answer = {"action": action, "x-response": {"ordered": [2, 1]}}
        if mode == "form":
            answer["content"] = {"value": "answer", "x-value": 42}
        final = await call(
            client,
            arguments=args,
            requestState=result["requestState"],
            inputResponses={key: answer},
        )
        assert final["result"]["resultType"] == "complete", final
        assert final["result"]["structuredContent"] == answer
        assert len(invocations) == 2


@pytest.mark.asyncio
async def test_new_round_uses_current_capabilities(elicitation_client):
    async with elicitation_client() as (client, _):
        first = (await call(client, name="Inputs_Twice", capabilities={"elicitation": {}}))[
            "result"
        ]
        key = next(iter(first["inputRequests"]))
        answer = {"action": "accept", "content": {"value": "first"}}
        second = (
            await call(
                client,
                name="Inputs_Twice",
                capabilities={"elicitation": {"url": {}}},
                requestState=first["requestState"],
                inputResponses={key: answer},
            )
        )["result"]
        key = next(iter(second["inputRequests"]))
        assert second["inputRequests"][key]["params"]["mode"] == "url"
        final = await call(
            client,
            name="Inputs_Twice",
            requestState=second["requestState"],
            inputResponses={key: {"action": "cancel"}},
        )
        assert final["result"]["structuredContent"] == {
            "first": answer,
            "second": {"action": "cancel"},
        }


@pytest.mark.asyncio
async def test_changed_arguments_are_rejected_before_author_code(elicitation_client):
    async with elicitation_client() as (client, invocations):
        first = (await call(client, arguments={"mode": "form"}, capabilities={"elicitation": {}}))[
            "result"
        ]
        key = next(iter(first["inputRequests"]))
        failed = await call(
            client,
            arguments={"mode": "url"},
            requestState=first["requestState"],
            inputResponses={key: {"action": "accept"}},
        )
        assert failed["error"]["code"] == -32602, failed
        assert "elicitation state" in failed["error"]["message"].lower(), failed
        assert invocations == ["form"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["signature", "expiry", "unsigned"])
async def test_continuation_state_rejects_forgery(elicitation_client, mutation):
    import base64
    import json

    async with elicitation_client() as (client, invocations):
        first = await call(
            client, arguments={"mode": "url"}, capabilities={"elicitation": {"url": {}}}
        )
        assert first["result"]["resultType"] == "input_required", (
            f"modern input request not delivered: {first}"
        )
        result = first["result"]
        state = result["requestState"]
        parts = state.split(".")
        if mutation == "signature":
            parts[-1] = ("B" if parts[-1][0] == "A" else "A") + parts[-1][1:]
        else:
            # Extend the real claims' expiry without changing the operation binding.
            # An unsigned implementation that merely compares arguments would accept this.
            claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
            claims["exp"] = 2524608000
            parts[1] = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
            if mutation == "unsigned":
                parts[0] = (
                    base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
                )
                parts[-1] = ""
        rejected = await call(
            client,
            arguments={"mode": "url"},
            requestState=".".join(parts),
            inputResponses={next(iter(result["inputRequests"])): {"action": "accept"}},
        )
        assert rejected.get("error", {}).get("code") == -32602, rejected
        assert "elicitation state" in rejected["error"]["message"].lower(), rejected
        assert invocations == ["url"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,capabilities",
    [
        ("form", {}),
        ("url", {}),
        ("form", {"elicitation": {"url": {}}}),
        ("url", {"elicitation": {"form": {}}}),
        ("url", {"elicitation": {}}),
    ],
)
async def test_undeclared_mode_returns_standard_capability_error(
    elicitation_client, mode, capabilities
):
    async with elicitation_client() as (client, invocations):
        response = await client.post(
            "/mcp/",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 42,
                "method": "tools/call",
                "params": {
                    "name": "Inputs_Ask",
                    "arguments": {"mode": mode},
                    "_meta": {
                        "io.modelcontextprotocol/protocolVersion": VERSION,
                        "io.modelcontextprotocol/clientCapabilities": capabilities,
                        "io.modelcontextprotocol/clientInfo": {"name": "proof", "version": "1"},
                    },
                },
            },
        )
        body = response.json()
        assert body.get("error", {}).get("code") == -32021, (
            f"authoring runtime did not return the standard missing-mode error: {body}"
        )
        assert response.status_code == 400
        assert body["id"] == 42
        assert body["error"]["data"]["requiredCapabilities"]["elicitation"] == {mode: {}}
        assert "result" not in body
        assert invocations == [mode]


@pytest.mark.asyncio
async def test_missing_capability_error_has_http_400_in_sse_mode(elicitation_client):
    async with elicitation_client(json_response=False) as (client, invocations):
        response = await client.post(
            "/mcp/",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 42,
                "method": "tools/call",
                "params": {
                    "name": "Inputs_Ask",
                    "arguments": {"mode": "url"},
                    "_meta": {
                        "io.modelcontextprotocol/protocolVersion": VERSION,
                        "io.modelcontextprotocol/clientCapabilities": {},
                    },
                },
            },
        )
        assert response.status_code == 400, "SSE missing-mode error committed HTTP 200"
        body = response.json()
        assert body["id"] == 42
        assert body["error"]["code"] == -32021
        assert body["error"]["data"]["requiredCapabilities"] == {"elicitation": {"url": {}}}
        assert "result" not in body
        assert invocations == ["url"]

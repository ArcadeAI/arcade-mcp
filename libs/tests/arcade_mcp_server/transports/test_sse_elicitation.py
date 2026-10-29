"""Positive SSE transport control for stateless elicitation."""

import json

import pytest
from test_http_elicitation import HEADERS, VERSION
from test_http_elicitation import elicitation_client as elicitation_client


@pytest.mark.asyncio
async def test_supported_mode_remains_an_sse_input_required_event(elicitation_client):
    async with elicitation_client(json_response=False) as (client, invocations):
        response = await client.post(
            "/mcp/",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 43,
                "method": "tools/call",
                "params": {
                    "name": "Inputs_Ask",
                    "arguments": {"mode": "url"},
                    "_meta": {
                        "io.modelcontextprotocol/protocolVersion": VERSION,
                        "io.modelcontextprotocol/clientCapabilities": {"elicitation": {"url": {}}},
                    },
                },
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        data = [
            line.removeprefix("data: ")
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        assert len(data) == 1
        body = json.loads(data[0])
        assert body["id"] == 43
        assert body["result"]["resultType"] == "input_required"
        assert next(iter(body["result"]["inputRequests"].values()))["params"]["mode"] == "url"
        assert body["result"]["requestState"]
        assert invocations == ["url"]

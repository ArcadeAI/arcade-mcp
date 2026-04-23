#!/usr/bin/env python3
"""sampling_with_tools MCP server.

Demonstrates tool calling in sampling (SEP-1577, MCP 2025-11-25):

- Pass ``tools=[...]`` and ``tool_choice={"mode": ...}`` to
  ``context.sampling.create_message``.
- When the client's model returns a ``tool_use`` content block, execute the
  corresponding helper locally and feed the result back with a
  ``tool_result`` block in a follow-up sampling call.
- ``tool_choice.mode`` values: ``"auto"`` (model decides), ``"required"``
  (model MUST call a tool), ``"none"`` (model MUST NOT call a tool).

Note: the *client's* model does the tool-calling; the server only defines
which tools the model may see and routes ``tool_use`` → local helper →
``tool_result``. This is different from regular MCP tool execution where the
*orchestrator's* model calls server tools — here it's a nested loop *inside*
a single server tool.
"""

import sys
from typing import Annotated, Any

from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.types import (
    SamplingMessage,
    TextContent,
    ToolResultContent,
    ToolUseContent,
)

app = MCPApp(
    name="sampling_with_tools",
    version="1.0.0",
    log_level="DEBUG",
    instructions=(
        "Each tool here uses the client's model via sampling and exposes a small set of "
        "local helpers that the model can call during sampling. The tool body loops until "
        "the model stops calling tools."
    ),
)


# -----------------------------------------------------------------------------
# Local helpers exposed to the client's model as "tools" inside sampling.
# These are NOT MCP tools — they're server-local Python functions we expose
# only inside the sampling request.
# -----------------------------------------------------------------------------


_FAKE_DOCS = {
    "mcp": "The Model Context Protocol is an open JSON-RPC standard for connecting AI models to tools and data sources.",
    "sampling": "Sampling lets a server ask the client's model to generate text, with optional tool calling (MCP 2025-11-25).",
    "tasks": "Tasks are durable long-running tool invocations introduced in MCP 2025-11-25.",
}


def _search_docs(query: str) -> str:
    """Mock docs lookup — returns the canned paragraph most similar to the query."""
    q = query.lower().strip()
    for key, body in _FAKE_DOCS.items():
        if key in q:
            return body
    return f"(no doc found for query {query!r})"


def _extract_entities(text: str) -> dict[str, Any]:
    """Extract a trivial set of "entities" — emails & capitalised words. Mock."""
    import re

    emails = re.findall(r"[\w.+-]+@[\w.-]+", text)
    capitalised = re.findall(r"\b[A-Z][a-z]+\b", text)
    return {"emails": emails, "entities": sorted(set(capitalised))}


# -----------------------------------------------------------------------------
# Helper: extract ToolUseContent blocks from whatever shape create_message returned
# -----------------------------------------------------------------------------


def _normalise_content(content: Any) -> list[Any]:
    """Flatten the content return into a list of content blocks.

    ``context.sampling.create_message`` returns either a single
    ``SamplingMessageContentBlock`` or a list of them.
    """
    if content is None:
        return []
    if isinstance(content, list):
        return list(content)
    return [content]


def _first_tool_use(blocks: list[Any]) -> ToolUseContent | None:
    for b in blocks:
        if isinstance(b, ToolUseContent):
            return b
        if isinstance(b, dict) and b.get("type") == "tool_use":
            return ToolUseContent(**b)
    return None


def _final_text(blocks: list[Any]) -> str:
    pieces = []
    for b in blocks:
        if isinstance(b, TextContent):
            pieces.append(b.text)
        elif isinstance(b, dict) and b.get("type") == "text":
            pieces.append(b.get("text", ""))
    return "\n".join(pieces).strip()


# -----------------------------------------------------------------------------
# 1. Auto tool choice — the model may or may not call a tool
# -----------------------------------------------------------------------------


@app.tool
async def research_with_lookup(
    context: Context,
    question: Annotated[str, "The question to answer"],
) -> Annotated[str, "The final answer from the model"]:
    """Ask the client's model to answer a question. The model may call the
    local ``search_docs`` tool as many times as it wants (``tool_choice.mode
    == "auto"``). When the model stops calling tools, we return its final text.
    """
    messages: list[SamplingMessage] = [
        SamplingMessage(
            role="user",
            content=TextContent(type="text", text=question),
        ),
    ]

    tools = [
        {
            "name": "search_docs",
            "description": "Look up a short doc paragraph for a topic.",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]

    # Cap the loop so a misbehaving model can't run forever.
    for _ in range(5):
        content = await context.sampling.create_message(
            messages=messages,
            system_prompt=(
                "You are a helpful assistant. If you need background on MCP, "
                "sampling, or tasks, call the `search_docs` tool."
            ),
            tools=tools,
            tool_choice={"mode": "auto"},
            max_tokens=512,
        )
        blocks = _normalise_content(content)
        tool_use = _first_tool_use(blocks)

        if tool_use is None:
            # Model finished — return the final text.
            return _final_text(blocks) or "(model returned no text)"

        # Model wants us to call search_docs. Run it locally.
        await context.log.info(f"Model called search_docs(query={tool_use.input!r})")
        tool_output = _search_docs(tool_use.input.get("query", ""))

        # Append assistant's tool_use + user's tool_result and loop.
        messages.append(
            SamplingMessage(role="assistant", content=[tool_use]),
        )
        messages.append(
            SamplingMessage(
                role="user",
                content=[
                    ToolResultContent(
                        type="tool_result",
                        toolUseId=tool_use.id,
                        content=[{"type": "text", "text": tool_output}],
                    )
                ],
            ),
        )

    return "(gave up: sampling loop exceeded max iterations)"


# -----------------------------------------------------------------------------
# 2. Required tool choice — the model MUST call the single tool
# -----------------------------------------------------------------------------


@app.tool
async def forced_extraction(
    context: Context,
    text: Annotated[str, "The text to extract entities from"],
) -> Annotated[dict, "Emails and capitalised words extracted by the model via tool_use"]:
    """Force the client's model to call ``extract_entities`` by setting
    ``tool_choice.mode == "required"``. Useful when the server knows the model
    should not reply in free-form text.
    """
    tools = [
        {
            "name": "extract_entities",
            "description": "Extract emails and entity-like capitalised words from the text.",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }
    ]

    content = await context.sampling.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=f"Please extract entities from:\n\n{text}"),
            ),
        ],
        tools=tools,
        tool_choice={"mode": "required"},
        max_tokens=256,
    )
    blocks = _normalise_content(content)
    tool_use = _first_tool_use(blocks)
    if tool_use is None:
        raise RuntimeError(
            "Model did not emit a tool_use block even though tool_choice.mode='required'. "
            "Either the client doesn't honour tool_choice.required or the model refused."
        )

    # Run the helper locally. Even though we forced the tool call, the server
    # decides what to do with the result — here we just return it so the caller
    # sees the extracted data directly.
    return _extract_entities(tool_use.input.get("text", text))


# -----------------------------------------------------------------------------
# 3. tool_choice="none" — the model is shown tools but cannot call them
# -----------------------------------------------------------------------------


@app.tool
async def summarize_with_none(
    context: Context,
    text: Annotated[str, "The text to summarize"],
) -> Annotated[str, "A summary from the model"]:
    """Pass ``tools=[...]`` but ``tool_choice.mode == "none"``. The model sees
    the available tools in its prompt (for context) but MUST NOT call them —
    useful when you want to reuse a single prompt template with / without
    tool use.

    The expected wire behaviour is that the model returns plain text.
    """
    content = await context.sampling.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=f"Summarize:\n\n{text}"),
            ),
        ],
        system_prompt="Respond with a one-sentence summary. Do not call any tools.",
        tools=[
            {
                "name": "search_docs",
                "description": "(not to be called here — shown for prompt parity with other tools)",
                "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
            }
        ],
        tool_choice={"mode": "none"},
        max_tokens=128,
    )
    blocks = _normalise_content(content)
    return _final_text(blocks) or "(model returned no text)"


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8000)

# sampling_with_tools

Demonstrates **tool calling inside sampling requests** — the 2025-11-25
addition from SEP-1577.

In a regular MCP flow, the orchestrator's model calls server tools. With
sampling-with-tools, a *server tool body* asks the *client's* model to
generate text and exposes a set of helpers the model may call *inside* that
generation. The server tool loops ``sampling/createMessage`` ↔
``tool_use/tool_result`` until the model stops calling tools, then returns
the final text to the orchestrator.

## What this example shows

| Tool | `tool_choice.mode` | Demonstrates |
|---|---|---|
| `research_with_lookup(question)` | `"auto"` | Model decides whether to call `search_docs`. The server loops until it stops. |
| `forced_extraction(text)` | `"required"` | Model MUST call the single `extract_entities` tool. |
| `summarize_with_none(text)` | `"none"` | Model sees tools but MUST NOT call them — the expected response is plain text. |

## Running

```bash
uv sync
uv run python src/sampling_with_tools/server.py        # stdio
uv run python src/sampling_with_tools/server.py http   # HTTP
```

You need an MCP client that (a) supports sampling and (b) advertised the
``sampling.tools`` capability during `initialize`. Otherwise the server
silently drops ``tools`` / ``toolChoice`` from the outgoing request (spec
requirement — servers MUST NOT send tool-enabled sampling to clients that
don't support it).

## Wire shape

A 2025-11-25 sampling request carrying tools looks like:

```jsonc
{
  "method": "sampling/createMessage",
  "params": {
    "messages": [
      {"role": "user", "content": {"type": "text", "text": "What is MCP?"}}
    ],
    "systemPrompt": "...",
    "maxTokens": 512,
    "tools": [
      {
        "name": "search_docs",
        "description": "...",
        "inputSchema": {"type": "object", "properties": {...}}
      }
    ],
    "toolChoice": {"mode": "auto"}
  }
}
```

When the client's model decides to call the tool, the response is:

```jsonc
{
  "role": "assistant",
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_...",
      "name": "search_docs",
      "input": {"query": "MCP"}
    }
  ],
  "model": "claude-sonnet-X",
  "stopReason": "tool_use"
}
```

The server then runs ``search_docs("MCP")`` locally, threads the result back
as a ``tool_result`` content block on a follow-up user message, and calls
``sampling/createMessage`` again:

```jsonc
{
  "messages": [
    {"role": "user", "content": {"type": "text", "text": "What is MCP?"}},
    {
      "role": "assistant",
      "content": [{"type": "tool_use", "id": "toolu_...", "name": "search_docs", "input": {...}}]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "toolUseId": "toolu_...",
          "content": [{"type": "text", "text": "The Model Context Protocol is..."}]
        }
      ]
    }
  ],
  "tools": [...],
  "toolChoice": {"mode": "auto"}
}
```

## Client capability gating

`context.sampling.create_message` checks `ClientCapabilities.sampling` at call
time. The session layer additionally checks `sampling.tools` specifically and
strips ``tools`` / ``toolChoice`` from the request if the client didn't opt in
— so a 2025-06-18 client still talks to this server, just without the tool
calling.

If you want to fail loudly instead of silently falling back to plain sampling,
inspect `context._session.negotiated_version` and
`context._session._client_capabilities.sampling` before calling, and raise
early.

## Validation: tool_use / tool_result shape rules

Server enforces (via `session._validate_sampling_messages`):

- A user message that contains ANY `tool_result` block MUST contain ONLY
  `tool_result` blocks.
- An assistant message with a `tool_use` block MUST be followed by a user
  message whose content is all `tool_result` blocks.

Violations raise `ValueError` before the request goes on the wire.

## Tested against

The wire shape matches what Claude Desktop / Cursor / VS Code implement as
the 2025-11-25 sampling surface. The exact tool-calling behaviour depends on
the model the client uses — Claude Sonnet honours `tool_choice={"mode":
"required"}` reliably; older models may need a nudge in the system prompt.

## Related SEPs

- **SEP-1577** — Tool calling in sampling.

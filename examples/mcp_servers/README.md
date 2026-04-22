# MCP Server Examples

Runnable examples demonstrating `arcade-mcp-server` features. Each directory is a self-contained Python package — copy one as a starting point for your own server.

```bash
cd examples/mcp_servers/<name>
uv sync
uv run python src/<name>/server.py         # stdio transport (default)
uv run python src/<name>/server.py http    # HTTP+SSE transport
```

| Example | Description |
|---|---|
| [`simple/`](simple/) | Minimal `MCPApp` with a couple of tools, a secret, and an OAuth-gated tool |
| [`echo/`](echo/) | Smallest possible server — one tool, stdio transport |
| [`logging/`](logging/) | Structured logging via `context.log.*` |
| [`progress_reporting/`](progress_reporting/) | Progress updates for long-running tools via `context.progress.report(...)` |
| [`sampling/`](sampling/) | Model-to-model sampling via `context.sampling.create_message(...)` |
| [`sampling_with_tools/`](sampling_with_tools/) | Tool calling inside a sampling loop |
| [`user_elicitation/`](user_elicitation/) | Form-mode user input via `context.ui.elicit(...)` |
| [`enum_elicitation/`](enum_elicitation/) | All five enum schema variants for elicitation (single/multi-select, titled/untitled, legacy) |
| [`url_elicitation/`](url_elicitation/) | Out-of-band user verification via URL-mode elicitation |
| [`resources/`](resources/) | MCP resources and resource templates via `@app.resource` |
| [`tool_chaining/`](tool_chaining/) | Tools calling other tools via `context.tools.call_raw(...)` |
| [`tool_metadata/`](tool_metadata/) | Behavior hints and extras via `@app.tool(metadata=ToolMetadata(...))` |
| [`tools_with_output_schema/`](tools_with_output_schema/) | Declaring `outputSchema` via typed return annotations |
| [`task_augmentation/`](task_augmentation/) | Long-running durable tool invocations via `ToolExecution.taskSupport` |
| [`typed_errors/`](typed_errors/) | Typed tool errors (`RetryableToolError`, `ContextRequiredToolError`, `UpstreamRateLimitError`, etc.) |
| [`server_branding/`](server_branding/) | Server icons, description, and `websiteUrl` in `InitializeResult.serverInfo` |
| [`authorization/`](authorization/) | OAuth 2.1 Resource Server Auth with PRM discovery and incremental scope consent |
| [`custom_server_with_prebuilt_tools/`](custom_server_with_prebuilt_tools/) | Mixing a custom `MCPApp` with an installed Arcade toolkit |
| [`local_filesystem/`](local_filesystem/) | A toolkit that reads and writes real local filesystem state |
| [`telemetry_passback/`](telemetry_passback/) | Emitting OpenTelemetry spans from a tool body |
| [`server_with_evaluations/`](server_with_evaluations/) | Tool catalog shipped alongside an `arcade_evals` test suite |

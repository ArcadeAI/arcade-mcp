# Write a server with tools that have MCP Apps

This server publishes a greeting editor. The editor can call the original tool
again or call a different tool in the same gateway.

| Tool                         | App action                                       | Authorization        |
| ---------------------------- | ------------------------------------------------ | -------------------- |
| `ToolsWithMcpApps.PreviewGreeting`   | Show the editor; preview an edited name          | None                 |
| `ToolsWithMcpApps.UppercaseGreeting` | Uppercase the greeting from the editor           | None                 |
| `ToolsWithMcpApps.GoogleProfile`     | Add the authorized Google account's display name | Google profile scope |

The first two tools work without Google setup. The third tool is an optional,
read-only example of authorization during an App interaction. It does not send
email or change account data.

## Run or deploy

From this directory:

```sh
uv sync --extra dev
uv run python src/tools_with_mcp_apps/server.py
```

The default transport is stdio. To publish the server through an Arcade gateway:

```sh
uv run arcade login
uv run arcade deploy -e src/tools_with_mcp_apps/server.py
```

Use the CLI's login command for the intended environment and project before
deploying. Before deploying a changed release, bump `project.version` in
`pyproject.toml` and run `uv sync --extra dev` again. The entrypoint reads that
installed package version; do not maintain a separate server version. When
changing the HTML App, also update its `appInfo.version` in `editor.html`.

The current managed deployment path has one toolkit, one active version, and
one replica. This example uses that path; it does not require multiple toolkits
or replicas.

In the Dashboard, create a gateway and select the three tools. Connect an MCP
Apps host to the gateway, then call `ToolsWithMcpApps_PreviewGreeting` with `name: "Ada"`.
Choose **Uppercase greeting** to call another tool. Create a second gateway
without `ToolsWithMcpApps.UppercaseGreeting` to check that the uppercase button is absent.
No resource picker or separate resource permission is required.

Managed resources must be enabled by the deployment operator, with a
resource-capable managed runtime already running on the deployed servers. A new
Engine image or configured runner image tag alone does not prove that existing
deployed servers have updated. See the platform's deployments guidance for
rollout and rollback checks.

## Declare the tool's UI

`src/tools_with_mcp_apps/ui.py` declares the HTML file, and `tools.py` attaches the resource
to the tool:

```python
@resource(file="editor.html", title="Greeting editor")
def editor() -> None:
    """Edit a greeting and call tools through the connected MCP host."""


@tool(ui=editor)
def preview_greeting(name: Annotated[str, "The name to greet"]) -> str:
    """Show a greeting editor."""
    return f"Hello, {name}!"
```

The framework publishes `ui://ToolsWithMcpApps/0.1.3/editor.html` with MIME type
`text/html;profile=mcp-app`. The gateway presents a globally unique resource URI
that includes the registered server's identity. The host reads the exact URI in
the tool's `_meta.ui.resourceUri`. Do not construct or decode that gateway URI
inside the App, and do not assume the App knows its server's identity.

This example's HTML is bundled with the package and is the same for every
end-user. Tool results and the host's tool availability responses supply runtime
data. Avoid embedding user credentials or per-user data in the HTML resource.

## Call a different tool

The App sends requests to its parent host. The host uses the existing gateway
connection; the iframe does not fetch the Engine API or hold an API key.

The central call in `editor.html` is:

```javascript
// `available` maps ToolsWithMcpApps.UppercaseGreeting to the exact returned MCP name.
const name = available.get("ToolsWithMcpApps.UppercaseGreeting")
const result = await request("tools/call", {
    name,
    arguments: { name: document.getElementById("name").value },
})
```

`request` is the small JSON-RPC/postMessage helper in this file. It initializes
the MCP Apps connection, accepts messages only from the parent, correlates
responses, and times out discovery requests. Tool calls can remain pending while
the host handles URL elicitation; the App does not abandon the response after
15 seconds. It is not a server-side tool call. With the
[official MCP Apps SDK](https://modelcontextprotocol.github.io/ext-apps/api/classes/app.App.html),
the equivalent call is `app.callServerTool({ name, arguments })`.

For this gateway, the wire request is:

```json
{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
        "name": "ToolsWithMcpApps_UppercaseGreeting",
        "arguments": { "name": "Grace" }
    }
}
```

The result is `HELLO, GRACE!`. The same request with the discovered
`ToolsWithMcpApps_PreviewGreeting` name resubmits to the original tool. Always call the
exact name returned by discovery, not a name guessed from a resource URI.
This example matches tool identities using the gateway's `Toolkit_Tool` naming.
An App for a server with different tool names must match that server's published
names instead; MCP does not prescribe Arcade's naming format.

## Check tool availability before editing

An App resource does not grant access to the tools the App calls. A gateway can
omit a tool, and the connected end-user's access policy can also omit a tool.

The editor first requests `tools/list`, as specified in the
[draft MCP Apps extension](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/draft/apps.mdx#standard-mcp-messages).
It collects every page and respects `_meta.ui.visibility`: a tool marked only
`["model"]` is not an App action. An omitted visibility defaults to model and App
visibility. The host may reject App messages; a draft feature is not a promise
that every host implements the feature.

If the host returns method-not-found (`-32601`), or its list exposes Arcade tool
recommendation tools rather than a complete callable-tool list, the editor uses
Arcade's existing temporary availability resource:

```text
arcade://gateway/tool-availability/v1?tool=ToolsWithMcpApps.PreviewGreeting&tool=ToolsWithMcpApps.UppercaseGreeting&tool=ToolsWithMcpApps.GoogleProfile&request=<fresh-uuid>
```

The App asks the host to `resources/read` that URI. The request is not a read of
the HTML document, and the UUID is a cache-busting nonce, not a credential. The
response contains one `application/json` resource whose text has this shape:

```json
{
    "version": 1,
    "tools": [
        {
            "tool": "ToolsWithMcpApps.PreviewGreeting",
            "name": "ToolsWithMcpApps_PreviewGreeting"
        },
        {
            "tool": "ToolsWithMcpApps.UppercaseGreeting",
            "name": "ToolsWithMcpApps_UppercaseGreeting"
        }
    ]
}
```

Only requested tools included in this gateway, permitted for this end-user,
and visible to the App are returned. This check does **not** check OAuth consent,
API keys, or tool secrets. The gateway recomputes availability on every request.
The fallback is tracked for removal in
[TOO-2155](https://linear.app/arcadedev/issue/TOO-2155); the code contains the same
TODO. New Apps must retain the fallback until the complete path supports native
App `tools/list`. Third-party Apps that do not use this convention are not
automatically given this behavior.

While discovery is pending or fails, the editor and action buttons are disabled.
A confirmed missing tool has no button. Other discovery errors are **unknown**,
not an empty tool list; **Check tools again** lets the user retry. The App checks
again before an action and on tool-list change notifications. Access can still
change between checking and calling, so an execution error remains possible.

## Handle authorization without losing edits

Availability means the tool can be called, not that the user has authorized the
tool. **Add Google profile** makes an ordinary tool call. The Engine applies the
normal consent, secrets, and execution policy; the App receives no extra rights.

A host that handles URL elicitation can complete authorization as part of that
interaction. If the host instead forwards an unresolved authorization response,
the example accepts the ordinary `authorization_url` result or a URL-elicitation
required error (`-32042`). The editor shows a prominent authorization prompt,
keeps the name, opens the authorization URL through `ui/open-link` when supported,
and exposes **Retry action**. Finishing OAuth never triggers another call by
itself. Retry uses the saved action arguments and rechecks tool availability.

If an initial call has not executed, show the authorization prompt rather than
an empty editor. The host must retry that originating call after authorization.
An ordinary execution or secret error is not converted into an OAuth prompt.
This example has no secret-requiring tool.

## HTTP(S) resources and release changes

The server also publishes `https://ToolsWithMcpApps/0.1.3/author-guide`. This is an MCP
resource identifier: the client retrieves the content with `resources/read`.
The identifier does not create a web endpoint. The gateway wraps the identifier
in a `resource://<server-key>/<encoded-original-uri>` routing address.

The resource preserves a separate public browser URL in `_meta.webUrl` and in
the text: `https://modelcontextprotocol.io/extensions/apps/overview`. `webUrl` is
author-supplied metadata, not a standard MCP field or a browser-navigation promise
from the host. Do not replace a genuine browser URL with the gateway address.

For the same registered server and exact original URI, a restart keeps the same
gateway address and serves the current published content. After a resource is
removed, its old address returns resource-not-found. A new toolkit package
version produces a different original URI in this framework; use the new
tool-linked URI instead of assuming an old UI address refers to the new release.

An older Python toolkit can publish no resources. The qualified managed runtime
handles that case: an initial upstream resource-list response of HTTP 404 or 405
means an empty resource list, and an unknown resource read means
resource-not-found. Other upstream failures remain failures. This compatibility
does not permit an old outer managed runtime; complete the runtime cutover first.

## Verify a deployment

Before marking a deployment verified, connect an unmodified MCP Apps host to the
deployed server's gateway. Check the full-tool and missing-uppercase gateways;
check a new end-user's Google authorization without revoking another user's
consent. Test the stateless and stateful gateway routes separately. Confirm that
`resources/read` returns the HTML and the HTTPS resource's `_meta.webUrl`. Record
real-host results separately from any simulated-host checks.

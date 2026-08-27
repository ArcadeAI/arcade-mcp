# Math with a user interface

A toolkit that ships a tool and the user interface for it, served over the worker
protocol.

`SumList` adds a list of numbers. `sum-list.html` is the interface a host would render
for it. The point of the example is the second one: a toolkit can declare a static
resource, the worker serves it under `/worker/resources/*`, and the engine fetches it
with every field intact.

## What is here

| File | What it does |
| -- | -- |
| `arcade_math/tools/arithmetic.py` | `@tool sum_list`, which resolves as `Math.SumList` |
| `arcade_math/ui/resources.py` | `@resource(path="sum-list.html")`, which resolves as `ui://math/0.1.0/sum-list.html` |
| `arcade_math/ui/sum_list.html` | The document itself, self-contained with no external assets |

An author writes the path. The framework builds the URI at registration from the
toolkit's name and installed version, so two toolkits in one worker image cannot collide
and the same toolkit at two versions stays distinguishable.

The mime type is `text/html;profile=mcp-app`, which the MCP Apps extension pins exactly.
The reference host compares it with string equality, so spacing and casing are part of
the value.

## Run it

Install, with the libs taken from this repository rather than PyPI:

```bash
cd examples/toolkits/math_ui && uv sync --extra dev
```

Start the worker. `ARCADE_WORKER_SECRET` is what turns on the `/worker/*` routes:

```bash
ARCADE_WORKER_SECRET=dev uv run python -m arcade_mcp_server http --host 127.0.0.1 --port 8020 --discover-installed --tool-package arcade_math
```

The startup log reports what it found:

```
Total tools loaded: 1
Total resources loaded: 1
Worker routes enabled at /worker/* (ARCADE_WORKER_SECRET is set)
```

Mint a token. The worker takes an HS256 JWT signed with the secret, audience `worker`.
`-W ignore` drops PyJWT's warning that a 3-byte key is shorter than RFC 7518 recommends for
HS256, which is true and is what `dev` is:

```bash
export TOKEN=$(uv run python -W ignore -c "import jwt,time; print(jwt.encode({'aud':'worker','ver':'1','iat':int(time.time()),'exp':int(time.time())+3600},'dev',algorithm='HS256'))")
```

List:

```bash
curl -s -X POST http://127.0.0.1:8020/worker/resources/list -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{}'
```

```json
{
  "resources": [
    {
      "name": "sum_list_ui",
      "title": "Sum a list of numbers",
      "uri": "ui://math/0.1.0/sum-list.html",
      "description": "Interface for the SumList tool: enter numbers, see the running total.",
      "mimeType": "text/html;profile=mcp-app"
    }
  ]
}
```

Read:

```bash
curl -s -X POST http://127.0.0.1:8020/worker/resources/read -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"uri":"ui://math/0.1.0/sum-list.html"}'
```

The response carries the document under `contents[0].text`, with the same mime type.

## Fetching it from the engine

The engine's resource client has a manual test that reads from a worker running on this
machine. With the worker above still up, from `apps/engine` in the monorepo:

```bash
WORKER_URL=http://127.0.0.1:8020 WORKER_SECRET=dev go test -tags manual ./internal/directors/workers/config/ -run TestManualWorkerResourcesEndToEnd -v
```

It lists, reads, and checks the mime type matches the listing byte for byte and that an
HTML document arrives as text rather than as a blob.

## What this example does not show

The tool does not advertise its interface. A host learns that a tool has one by reading
`_meta.ui.resourceUri` off the tool, and `ToolDefinition` has no `_meta` field yet, so
nothing here connects `Math.SumList` to `ui://math/0.1.0/sum-list.html` except the two
being in the same toolkit. Nothing renders the document either. Both sit above this leg.

## Notes

The distribution is named `arcade_math` so the tool reads as `Math.SumList`, which
shadows the published toolkit of the same name. Install it in its own virtual
environment, which `uv sync` does here by default. Examples are excluded from the release
workflow, so this is never published.

Resources are found through installed-package discovery. Pointing the server at a
directory of loose Python files finds the tools in them and none of the resources.

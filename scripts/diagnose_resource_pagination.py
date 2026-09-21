"""Local resource pagination fixture: real worker handlers behind one URL per scenario.

Run with ``uv run uvicorn scripts.diagnose_resource_pagination:app --host 127.0.0.1
--port 58145``. The dispatcher deterministically changes replica on continuation;
it never constructs a resource response or decodes a worker cursor. All data and
the worker secret are synthetic. This is diagnostic evidence, not a deployed proxy.
"""

import httpx
from arcade_core.resource_schema import Resource
from arcade_serve.fastapi.worker import FastAPIWorker
from fastapi import FastAPI, Request, Response

WORKER_SECRET = "resource-pagination-test-secret"  # noqa: S105 — local test fixture only


def replica(uris: list[str], page_size: int) -> FastAPI:
    app = FastAPI()
    worker = FastAPIWorker(app=app, secret=WORKER_SECRET)
    worker.catalog.resources.page_size = page_size
    for uri in uris:
        worker.catalog.resources.add(Resource(uri=uri, name=uri), "synthetic resource")
    return app


def math_uris(version: str, names: list[str]) -> list[str]:
    return [f"ui://Math/{version}/{name}.html" for name in names]


small = math_uris("1.1.0", ["a", "b"])
large = math_uris("1.1.0", [f"page-{i:03}" for i in range(251)])
cases = {
    "equivalent": (replica(small, 1), replica(list(reversed(small)), 1)),
    "downgrade": (replica(small, 1), replica(math_uris("1.0.0", ["a", "b"]), 1)),
    "nonempty": (
        replica(math_uris("1.1.0", ["a", "b", "c", "d"]), 2),
        replica(math_uris("1.1.0", ["aa", "b", "d", "e"]), 2),
    ),
    "equivalent-default": (replica(large, 250), replica(list(reversed(large)), 250)),
    "downgrade-default": (
        replica(large, 250),
        replica(math_uris("1.0.0", [f"page-{i:03}" for i in range(251)]), 250),
    ),
    "legacy-404": (replica(large, 250), FastAPI()),
}
app = FastAPI()


@app.post("/{scenario}/worker/resources/list")
async def list_resources(scenario: str, request: Request) -> Response:
    body = await request.body()
    params = await request.json()
    first, continuation = cases[scenario]
    selected = continuation if params.get("cursor") else first
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=selected), base_url="http://worker.test"
    ) as client:
        response = await client.post(
            "/worker/resources/list",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": request.headers.get("Authorization", ""),
            },
        )
    return Response(
        response.content, status_code=response.status_code, media_type="application/json"
    )

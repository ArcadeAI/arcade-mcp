"""
Shared HTTP transport helpers for org-scoped Arcade API access.
"""

from __future__ import annotations

import httpx


def _rewrite_request_path(request: httpx.Request, org_id: str, project_id: str) -> httpx.Request:
    """Return a request with its path rewritten to include org/project scope."""
    path = request.url.path
    if path.startswith("/v1/") and "/v1/orgs/" not in path:
        scoped_path = path.replace("/v1/", f"/v1/orgs/{org_id}/projects/{project_id}/", 1)
        scoped_url = request.url.copy_with(path=scoped_path)
        return httpx.Request(
            method=request.method,
            url=scoped_url,
            headers=request.headers,
            content=request.content,
            extensions=request.extensions,
        )
    return request


class OrgScopedTransport(httpx.BaseTransport):
    """Sync transport that rewrites requests to include org/project scope."""

    def __init__(
        self,
        wrapped_transport: httpx.BaseTransport,
        org_id: str,
        project_id: str,
    ) -> None:
        self.wrapped = wrapped_transport
        self.org_id = org_id
        self.project_id = project_id

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        scoped_request = _rewrite_request_path(request, self.org_id, self.project_id)
        return self.wrapped.handle_request(scoped_request)

    def close(self) -> None:
        self.wrapped.close()


class AsyncOrgScopedTransport(httpx.AsyncBaseTransport):
    """Async transport that rewrites requests to include org/project scope."""

    def __init__(
        self,
        wrapped_transport: httpx.AsyncBaseTransport,
        org_id: str,
        project_id: str,
    ) -> None:
        self.wrapped = wrapped_transport
        self.org_id = org_id
        self.project_id = project_id

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        scoped_request = _rewrite_request_path(request, self.org_id, self.project_id)
        return await self.wrapped.handle_async_request(scoped_request)

    async def aclose(self) -> None:
        await self.wrapped.aclose()


def build_org_scoped_http_client(
    org_id: str,
    project_id: str,
    *,
    base_transport: httpx.BaseTransport | None = None,
    client_kwargs: dict | None = None,
) -> httpx.Client:
    """
    Build a sync httpx.Client that rewrites /v1 requests with org/project scope.
    """
    client_kwargs = client_kwargs or {}
    transport = OrgScopedTransport(
        base_transport or httpx.HTTPTransport(), org_id=org_id, project_id=project_id
    )
    return httpx.Client(transport=transport, **client_kwargs)


def build_org_scoped_async_http_client(
    org_id: str,
    project_id: str,
    *,
    base_transport: httpx.AsyncBaseTransport | None = None,
    client_kwargs: dict | None = None,
) -> httpx.AsyncClient:
    """
    Build an async httpx.AsyncClient that rewrites /v1 requests with org/project scope.
    """
    client_kwargs = client_kwargs or {}
    transport = AsyncOrgScopedTransport(
        base_transport or httpx.AsyncHTTPTransport(), org_id=org_id, project_id=project_id
    )
    return httpx.AsyncClient(transport=transport, **client_kwargs)

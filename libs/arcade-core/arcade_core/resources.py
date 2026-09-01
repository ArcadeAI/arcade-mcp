"""The resource registry: what a worker can serve for ``resources/*``.

Resources on this path are static. Contents are resolved once, when a toolkit
is registered, and held. Nothing is executed on the request path, so the
endpoints that read this registry stay a serialization shim.
"""

from __future__ import annotations

import base64
import binascii
import inspect
from bisect import bisect_right, insort
from dataclasses import dataclass

from arcade_core.resource_schema import (
    BlobResourceContents,
    Resource,
    TextResourceContents,
)

DEFAULT_PAGE_SIZE = 250

_CURSOR_PREFIX = "after:"


class InvalidCursorError(ValueError):
    """Raised when a caller sends a cursor this registry did not issue."""


class ResourceNotFoundError(KeyError):
    """Raised when no resource is registered at the requested URI."""


def encode_cursor(last_uri: str) -> str:
    """A cursor names the last URI served, not how many were served before it.

    A worker runs as several processes and a page can be served by a different
    one than issued the cursor. An index is only the same position in both when
    both hold the same URIs, and they do not: a toolkit version lives in the
    URI, so mid-rollout one replica holds ``ui://Math/1.1.0/x`` where another
    holds ``ui://Math/1.0.0/x``. The same offset then skips, repeats, or ends
    the listing early. A URI is the same position in any replica that has it,
    and a resume point in any replica that does not.

    Opaque to callers, so the encoding can still change freely.
    """
    raw = f"{_CURSOR_PREFIX}{last_uri}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> str:
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError(f"malformed cursor: {cursor!r}") from exc
    if not raw.startswith(_CURSOR_PREFIX):
        raise InvalidCursorError(f"malformed cursor: {cursor!r}")
    last_uri = raw[len(_CURSOR_PREFIX) :]
    if not last_uri:
        raise InvalidCursorError(f"malformed cursor: {cursor!r}")
    return last_uri


@dataclass(frozen=True)
class RegisteredResource:
    """A listing entry and the bytes it resolves to."""

    resource: Resource
    contents: TextResourceContents | BlobResourceContents


class ResourceRegistry:
    """URI to resource, beside the tool catalog and independent of it."""

    def __init__(self, page_size: int = DEFAULT_PAGE_SIZE) -> None:
        self._resources: dict[str, RegisteredResource] = {}
        self._uris: list[str] = []
        self.page_size = page_size

    @property
    def page_size(self) -> int:
        return self._page_size

    @page_size.setter
    def page_size(self, value: int) -> None:
        # Validated on assignment, not just in __init__, because this is a public
        # attribute callers set directly. A non-positive size makes cursor paging
        # non-terminating: zero hands back an empty page and the same cursor
        # forever, and a negative one walks the offset backwards into a cursor
        # this registry then rejects as malformed.
        if value <= 0:
            raise ValueError(f"page_size must be positive, got {value}")
        self._page_size = value

    def __len__(self) -> int:
        return len(self._resources)

    def __contains__(self, uri: object) -> bool:
        return uri in self._resources

    def add(self, resource: Resource, contents: str | bytes) -> RegisteredResource:
        """Register a resource at its own URI, replacing any resource already there.

        Text and binary are kept apart by type rather than by emptiness, so a
        zero-length document and a zero-length blob stay distinguishable all the
        way to the client.
        """
        if not isinstance(contents, (str, bytes)):
            # Checked on the value rather than on the function, because any check
            # against the function object is defeatable by a wrapper: a synchronous
            # def returning a coroutine passes iscoroutinefunction and still lands
            # here holding one.
            hint = (
                " A resource is resolved once at registration on a synchronous path,"
                " so it cannot return a coroutine."
                if inspect.iscoroutine(contents)
                else ""
            )
            raise TypeError(
                f"resource contents for {resource.uri} must be str or bytes, "
                f"got {type(contents).__name__}.{hint}"
            )

        if isinstance(contents, bytes):
            body: TextResourceContents | BlobResourceContents = BlobResourceContents(
                uri=resource.uri,
                mimeType=resource.mimeType,
                blob=base64.b64encode(contents).decode("ascii"),
            )
        else:
            body = TextResourceContents(
                uri=resource.uri,
                mimeType=resource.mimeType,
                text=contents,
            )

        registered = RegisteredResource(resource=resource, contents=body)
        if resource.uri not in self._resources:
            insort(self._uris, resource.uri)
        self._resources[resource.uri] = registered
        return registered

    def get(self, uri: str) -> RegisteredResource:
        try:
            return self._resources[uri]
        except KeyError:
            raise ResourceNotFoundError(uri) from None

    def list(self, cursor: str | None = None) -> tuple[list[Resource], str | None]:
        """Return one page of resources and the cursor for the next, if any.

        A worker registers once at startup and lists on every request, so the
        ordering cost sits on the write. ``add`` keeps ``_uris`` sorted and this
        is a slice.

        Ordering is by URI so a cursor keeps its meaning when the next page is
        served by a different process. A worker can run as several processes
        behind one address, and none of them shares insertion order.

        The cursor names a URI and the resume point is found with a binary
        search, so a replica that does not hold that exact URI still resumes
        after where it would sort rather than at some unrelated index.
        """
        start = bisect_right(self._uris, decode_cursor(cursor)) if cursor else 0
        end = start + self.page_size
        window = self._uris[start:end]
        page = [self._resources[uri].resource for uri in window]
        next_cursor = encode_cursor(window[-1]) if window and end < len(self._uris) else None
        return page, next_cursor

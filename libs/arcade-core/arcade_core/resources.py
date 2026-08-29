"""The resource registry: what a worker can serve for ``resources/*``.

Resources on this path are static. Contents are resolved once, when a toolkit
is registered, and held. Nothing is executed on the request path, so the
endpoints that read this registry stay a serialization shim.
"""

from __future__ import annotations

import base64
import binascii
import inspect
from bisect import insort
from dataclasses import dataclass

from arcade_core.resource_schema import (
    BlobResourceContents,
    Resource,
    TextResourceContents,
)

DEFAULT_PAGE_SIZE = 250

_CURSOR_PREFIX = "offset:"

#: The scheme a tool's user interface is addressed under. Hosts that render an
#: interface require it and refuse anything else.
UI_SCHEME = "ui"


class InvalidCursorError(ValueError):
    """Raised when a caller sends a cursor this registry did not issue."""


class ResourceNotFoundError(KeyError):
    """Raised when no resource is registered at the requested URI."""


def encode_cursor(offset: int) -> str:
    """Cursors are opaque to callers, so the encoding can change freely."""
    raw = f"{_CURSOR_PREFIX}{offset}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> int:
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError(f"malformed cursor: {cursor!r}") from exc
    if not raw.startswith(_CURSOR_PREFIX):
        raise InvalidCursorError(f"malformed cursor: {cursor!r}")
    try:
        offset = int(raw[len(_CURSOR_PREFIX) :])
    except ValueError as exc:
        raise InvalidCursorError(f"malformed cursor: {cursor!r}") from exc
    if offset < 0:
        raise InvalidCursorError(f"malformed cursor: {cursor!r}")
    return offset


class InvalidResourcePathError(ValueError):
    """Raised when a declared path cannot be qualified into a URI."""


def qualify(toolkit_name: str, toolkit_version: str, path: str, scheme: str = UI_SCHEME) -> str:
    """Build the toolkit-qualified URI for a resource a toolkit declares.

    ``ui://Gmail/8.1.0/draft-review.html``. The toolkit segment separates two
    toolkits packed into one worker image; the version segment separates the
    same toolkit installed at two versions across two workers, which is what
    keeps a tool and its interface in agreement.

    The scheme is carried through and never replaced. A host that renders a
    tool's interface requires ``ui://`` and throws on anything else, so a
    prefix-replacing qualifier breaks rendering outright.
    """
    scheme = scheme.rstrip(":/")
    if not scheme:
        raise InvalidResourcePathError("a resource URI needs a scheme")
    if not toolkit_name:
        raise InvalidResourcePathError("a resource URI needs a toolkit name")
    if not toolkit_version:
        raise InvalidResourcePathError("a resource URI needs a toolkit version")

    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        raise InvalidResourcePathError(f"a resource needs a path: {path!r}")
    if any(segment in (".", "..") for segment in segments):
        raise InvalidResourcePathError(f"a resource path may not traverse: {path!r}")

    # A path may not carry a character that changes what the URI means or stops
    # it being one. "?" opens a query and "#" opens a fragment, so either would
    # leave the resource registered under a string whose path component is
    # shorter than the author wrote; a control character makes the URI fail to
    # parse at all. Both fail at the point of reading, far from the declaration.
    for char in path:
        if char in "?#":
            raise InvalidResourcePathError(
                f"a resource path may not contain {char!r}, which starts a new URI component: {path!r}"
            )
        if not char.isprintable():
            raise InvalidResourcePathError(
                f"a resource path may not contain a control character: {path!r}"
            )

    return f"{scheme}://{toolkit_name}/{toolkit_version}/{'/'.join(segments)}"


@dataclass(frozen=True)
class ResourceDeclaration:
    """What a toolkit author writes. The URI is derived, never typed."""

    path: str
    name: str
    scheme: str = UI_SCHEME
    title: str | None = None
    description: str | None = None
    mime_type: str | None = None


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

    def declare(
        self,
        declaration: ResourceDeclaration,
        contents: str | bytes,
        *,
        toolkit_name: str,
        toolkit_version: str,
    ) -> RegisteredResource:
        """Register a toolkit's declaration, qualifying its URI on the way in.

        Qualification happens here because this is the only point where the
        declaration and the toolkit's identity are both in scope.
        """
        uri = qualify(toolkit_name, toolkit_version, declaration.path, declaration.scheme)
        resource = Resource(
            uri=uri,
            name=declaration.name,
            title=declaration.title,
            description=declaration.description,
            mimeType=declaration.mime_type,
        )
        return self.add(resource, contents)

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
        """
        offset = decode_cursor(cursor) if cursor else 0
        window = self._uris[offset : offset + self.page_size]
        page = [self._resources[uri].resource for uri in window]
        next_offset = offset + self.page_size
        next_cursor = encode_cursor(next_offset) if next_offset < len(self._uris) else None
        return page, next_cursor

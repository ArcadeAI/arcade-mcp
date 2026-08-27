"""Resource schema for the worker format.

The shapes a worker returns when a caller lists or reads the resources a
toolkit ships: a listing entry, its contents as text or as a base64 blob, and
the paginated results that carry them.

Field names are spelled exactly as they go on the wire, including the
underscore on ``_meta``, so nothing has to be renamed at either end.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Cursor = str
Role = Literal["user", "assistant"]


class Result(BaseModel):
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class PaginatedResult(Result):
    nextCursor: Cursor | None = None


class BaseMetadata(BaseModel):
    name: str
    title: str | None = None

    # populate_by_name lets callers pass ``meta=`` for the ``_meta`` field. Without
    # it, and with extra="allow", ``meta=`` is silently accepted as an extra field
    # and serialized as ``meta``, which no caller reads.
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Icon(BaseModel):
    """Icon metadata."""

    src: str
    mimeType: str | None = None
    sizes: list[str] | None = None
    theme: Literal["light", "dark"] | None = None

    model_config = ConfigDict(extra="allow")


class Annotations(BaseModel):
    audience: list[Role] | None = None
    priority: float | None = None
    lastModified: str | None = None

    model_config = ConfigDict(extra="allow")


class Resource(BaseMetadata):
    uri: str
    description: str | None = None
    mimeType: str | None = None
    annotations: Annotations | None = None
    size: int | None = None
    icons: list[Icon] | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ListResourcesParams(BaseModel):
    """Params for a resource listing request: an optional pagination cursor."""

    cursor: Cursor | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ListResourcesResult(PaginatedResult):
    resources: list[Resource] = Field(default_factory=list)


class ResourceTemplate(BaseMetadata):
    uriTemplate: str
    description: str | None = None
    mimeType: str | None = None
    annotations: Annotations | None = None
    icons: list[Icon] | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ListResourceTemplatesResult(PaginatedResult):
    resourceTemplates: list[ResourceTemplate] = Field(default_factory=list)


class ReadResourceParams(BaseModel):
    uri: str


class ResourceContents(BaseModel):
    uri: str
    mimeType: str | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)

    model_config = ConfigDict(populate_by_name=True)


class TextResourceContents(ResourceContents):
    text: str


class BlobResourceContents(ResourceContents):
    blob: str


class ReadResourceResult(Result):
    contents: list[TextResourceContents | BlobResourceContents]

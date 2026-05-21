"""Precomputed catalog manifest.

Allows a built worker image to skip toolkit discovery and tool-schema
materialization at startup by reading a pre-built JSON file produced
at image-build time. The runtime catalog still imports toolkit modules
lazily on first ``tools/call`` for each toolkit.
"""

from __future__ import annotations

import importlib.metadata
import json
import logging
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import cast

from pydantic import BaseModel, Field

from arcade_core.schema import ToolDefinition

logger = logging.getLogger(__name__)

MANIFEST_SCHEMA_VERSION = "1"


class PackageVersion(BaseModel):
    """Package name + version pinned at manifest-build time."""

    name: str
    version: str


class ManifestEntry(BaseModel):
    """One tool's persisted record.

    The Python function name (``function_name``) is stored separately from
    ``definition.name``: the former is the raw identifier used to
    ``getattr(module, function_name)`` at execution time, while the latter
    is the PascalCase name surfaced to clients.

    ``tool_context_parameter_name`` mirrors
    ``ToolDefinition.input.tool_context_parameter_name`` because that field
    is ``exclude=True`` in pydantic and would otherwise be dropped on
    serialization, leaving ``ToolExecutor`` unable to inject the
    ``Context`` argument at call time.
    """

    module_name: str
    function_name: str
    toolkit_name: str
    toolkit_version: str | None = None
    toolkit_description: str | None = None
    package_name: str | None = None
    tool_context_parameter_name: str | None = None
    definition: ToolDefinition


class CatalogManifest(BaseModel):
    """A precomputed tool catalog, durable across processes."""

    schema_version: str = MANIFEST_SCHEMA_VERSION
    package_versions: list[PackageVersion] = Field(default_factory=list)
    entries: list[ManifestEntry] = Field(default_factory=list)


def build_manifest(catalog: object) -> CatalogManifest:
    """Walk a ToolCatalog and produce a serializable manifest.

    Imported lazily to avoid a circular import between ``catalog`` and
    ``manifest`` at module load time.
    """
    from arcade_core.catalog import ToolCatalog  # local to break import cycle

    if not isinstance(catalog, ToolCatalog):
        raise TypeError(f"Expected ToolCatalog, got {type(catalog).__name__}")

    entries: list[ManifestEntry] = []
    packages: dict[str, str] = {}

    for materialized_tool in catalog:
        meta = materialized_tool.meta
        definition = materialized_tool.definition
        function_name = getattr(materialized_tool.tool, "__name__", definition.name)

        entries.append(
            ManifestEntry(
                module_name=meta.module,
                function_name=function_name,
                toolkit_name=definition.toolkit.name,
                toolkit_version=definition.toolkit.version,
                toolkit_description=definition.toolkit.description,
                package_name=meta.package,
                tool_context_parameter_name=definition.input.tool_context_parameter_name,
                definition=definition,
            )
        )

        if meta.package and meta.package not in packages:
            try:
                packages[meta.package] = importlib.metadata.version(meta.package)
            except importlib.metadata.PackageNotFoundError:
                continue

    return CatalogManifest(
        package_versions=[PackageVersion(name=n, version=v) for n, v in sorted(packages.items())],
        entries=entries,
    )


def write_manifest(catalog: object, path: str | Path) -> Path:
    """Build a manifest for ``catalog`` and write it to ``path``.

    Returns the resolved output path. The parent directory must exist.
    """
    out = Path(path)
    manifest = build_manifest(catalog)
    out.write_text(manifest.model_dump_json(indent=2))
    return out


class IncompatibleManifestError(ValueError):
    """Raised when a manifest's ``schema_version`` does not match this runtime."""


def load_manifest(path: str | Path) -> CatalogManifest:
    """Load a manifest from disk and validate it.

    Raises:
        IncompatibleManifestError: if the on-disk ``schema_version`` doesn't
            match :data:`MANIFEST_SCHEMA_VERSION`. Older manifests can lack
            fields the runtime depends on (e.g. ``tool_context_parameter_name``
            was added between versions), so silent acceptance would produce
            tools that pass ``/worker/tools`` but fail on first call.
    """
    raw = Path(path).read_text()
    data = json.loads(raw)
    on_disk_version = data.get("schema_version")
    if on_disk_version != MANIFEST_SCHEMA_VERSION:
        raise IncompatibleManifestError(
            f"Catalog manifest at {path} has schema_version={on_disk_version!r} "
            f"but this runtime expects {MANIFEST_SCHEMA_VERSION!r}. "
            f"Rebuild with: python -m arcade_mcp_server build-manifest --output {path}"
        )
    return CatalogManifest.model_validate(data)


def check_manifest_staleness(manifest: CatalogManifest) -> list[str]:
    """Compare the manifest's pinned package versions against the live install.

    Returns a list of human-readable warning strings (one per mismatch).
    Caller decides whether to log, fail, or ignore. An empty list means
    every recorded package matches what is currently importable.
    """
    warnings: list[str] = []
    for pkg in manifest.package_versions:
        try:
            current = importlib.metadata.version(pkg.name)
        except importlib.metadata.PackageNotFoundError:
            warnings.append(
                f"manifest references {pkg.name}=={pkg.version} but the package is not installed"
            )
            continue
        if current != pkg.version:
            warnings.append(f"manifest pinned {pkg.name}=={pkg.version} but {current} is installed")
    return warnings


class ManifestToolResolutionError(RuntimeError):
    """Raised when a manifest-declared tool cannot be resolved from its module.

    Indicates a stale manifest: the toolkit was uninstalled, renamed, or had
    the function removed between manifest build and runtime.
    """


def make_tool_factory(module_name: str, function_name: str) -> Callable[[], Callable[..., object]]:
    """Return a zero-arg callable that imports the module and returns the function.

    Used by ``ToolCatalog.from_manifest`` to defer toolkit imports until
    the first ``tools/call`` for that toolkit. Captures by value so the
    closure is safe across loop iterations. Surfaces import/attribute
    errors as ``ManifestToolResolutionError`` so the caller can distinguish
    "manifest stale" from "the tool function itself raised at import".
    """

    def _resolve() -> Callable[..., object]:
        try:
            module = import_module(module_name)
        except ImportError as exc:
            raise ManifestToolResolutionError(
                f"Manifest references module '{module_name}' (function "
                f"'{function_name}') but the module cannot be imported. "
                f"Reason: {exc}. The manifest is likely stale — rebuild with "
                f"python -m arcade_mcp_server build-manifest."
            ) from exc
        try:
            return cast("Callable[..., object]", getattr(module, function_name))
        except AttributeError as exc:
            raise ManifestToolResolutionError(
                f"Manifest references function '{function_name}' in module "
                f"'{module_name}' but the attribute does not exist. "
                f"The manifest is likely stale — rebuild with "
                f"python -m arcade_mcp_server build-manifest."
            ) from exc

    _resolve.__qualname__ = f"manifest_resolver[{module_name}.{function_name}]"
    return _resolve

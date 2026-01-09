from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, cast

from arcade_core.schema import ToolContext

DatacacheKey = Literal["organization", "project", "user_id"]
DatacacheKeys = list[DatacacheKey]
DEFAULT_ORGANIZATION_IDENTITY = "default"
DEFAULT_PROJECT_IDENTITY = "default"


class DatacacheConfig(TypedDict, total=False):
    keys: DatacacheKeys
    ttl: int


class DatacacheConfigError(ValueError):
    pass


def is_datacache_enabled(cfg: dict[str, Any] | None) -> bool:
    """Datacache is enabled only if `keys` exists (per product spec)."""
    return bool(cfg) and "keys" in cast(dict[str, Any], cfg)


def _normalize_keys(keys: Any) -> DatacacheKeys:
    if not isinstance(keys, list) or any(not isinstance(k, str) for k in keys):
        raise DatacacheConfigError("datacache.keys must be a list of strings")
    allowed: set[str] = {"organization", "project", "user_id"}
    normalized: list[DatacacheKey] = []
    for k in keys:
        k_lower = str(k).strip().lower()
        if k_lower not in allowed:
            raise DatacacheConfigError(
                f"Unsupported datacache key '{k}'. Allowed: organization, project, user_id"
            )
        normalized.append(cast(DatacacheKey, k_lower))
    # de-dupe while preserving order
    seen: set[DatacacheKey] = set()
    out: list[DatacacheKey] = []
    for k in normalized:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _normalize_ttl(ttl: Any) -> int | None:
    if ttl is None:
        return None
    if not isinstance(ttl, int) or ttl < 0:
        raise DatacacheConfigError("datacache.ttl must be a non-negative integer (seconds)")
    return ttl


def parse_datacache_config(cfg: dict[str, Any] | None) -> DatacacheConfig | None:
    if not cfg:
        return None
    if not isinstance(cfg, dict):
        raise DatacacheConfigError("datacache must be an object/dict")
    out: DatacacheConfig = {}
    if "keys" in cfg:
        out["keys"] = _normalize_keys(cfg.get("keys"))
    if "ttl" in cfg:
        ttl = _normalize_ttl(cfg.get("ttl"))
        if ttl is not None:
            out["ttl"] = ttl
    return out


def _get_metadata(tool_context: ToolContext, key: str) -> str | None:
    if not tool_context.metadata:
        return None
    key_norm = key.lower()
    for item in tool_context.metadata:
        if item.key.lower() == key_norm:
            return item.value
    return None


@dataclass(frozen=True)
class DatacacheIdentity:
    """Resolved identity for a datacache instance."""

    toolkit: str
    key_parts: dict[str, str]
    cache_key: str
    cache_key_slug: str


_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _slugify(value: str, *, max_len: int = 200) -> str:
    """Create a filesystem/redis/s3-safe slug."""
    value = value.strip()
    value = _SLUG_RE.sub("_", value)
    value = value.strip("._-")
    if not value:
        value = "default"
    if len(value) > max_len:
        value = value[:max_len]
    return value


def build_datacache_identity(
    *,
    tool_fqn: str,
    cfg: DatacacheConfig,
    tool_context: ToolContext,
) -> DatacacheIdentity:
    # Identity is scoped to the toolkit (not the individual tool) so tools can share tables.
    toolkit = tool_fqn.split(".", 1)[0] if "." in tool_fqn else tool_fqn
    keys = cfg.get("keys") or []
    key_parts: dict[str, str] = {}
    for k in keys:
        if k == "user_id":
            if not tool_context.user_id:
                raise DatacacheConfigError(
                    "datacache key 'user_id' requested but ToolContext.user_id is empty"
                )
            key_parts["user_id"] = tool_context.user_id
        elif k == "organization":
            val = _get_metadata(tool_context, "organization")
            # If organization is missing/null, use the default identity.
            key_parts["organization"] = val if val else DEFAULT_ORGANIZATION_IDENTITY
        elif k == "project":
            val = _get_metadata(tool_context, "project")
            # If project is missing/null, use the default identity.
            key_parts["project"] = val if val else DEFAULT_PROJECT_IDENTITY

    # Human-readable cache key for debugging/ops (also slugified for storage/locks).
    # Keep ASCII-safe and avoid '=' in the slug. Use `--` separators.
    cache_key = (
        f"toolkit--{toolkit}--"
        f"org--{key_parts.get('organization', '')}--"
        f"project--{key_parts.get('project', '')}--"
        f"user--{key_parts.get('user_id', '')}"
    )
    cache_key_slug = _slugify(cache_key)
    return DatacacheIdentity(
        toolkit=toolkit,
        key_parts=key_parts,
        cache_key=cache_key,
        cache_key_slug=cache_key_slug,
    )

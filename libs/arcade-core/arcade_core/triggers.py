"""Trigger-type declarations.

Toolkits declare trigger types as data; the worker serves them to the engine
alongside tool definitions. Validation is load-time: a broken declaration must
fail toolkit load, never reach the wire.
"""

from typing import Any, Literal

from pydantic import BaseModel


class TriggerType(BaseModel):
    """A toolkit-declared trigger type."""

    slug: str
    """Toolkit-namespaced identifier, e.g. "slack.message.received"."""

    name: str
    """Human-readable name shown in catalogues."""

    description: str
    """What the trigger watches for."""

    kind: Literal["webhook", "poll"]
    """Transport kind: provider-pushed webhook or engine-driven poll."""

    config_schema: dict[str, Any]
    """JSON Schema that per-instance config is validated against."""

    payload_schema: dict[str, Any]
    """Schema of the normalized event delivered on fire."""

    sample_payload: dict[str, Any]
    """Example payload for test-trigger UX and catalogue previews."""

    version: str
    """Declaration version; rides the toolkit version axis."""

    instructions: str | None = None
    """Setup guidance shown in the dashboard."""

    verification: dict[str, Any] | None = None
    """Webhook-kind: named verification scheme and params executed at ingress."""

    normalize_handler: str | None = None
    """Webhook-kind: tool reference invoked to normalize raw provider events."""

    poll_handler: str | None = None
    """Poll-kind: tool reference invoked on the polling cadence."""

    default_interval: int | None = None
    """Poll-kind: default polling interval in seconds."""

    dedupe: Literal["unique", "greatest", "last"] | None = None
    """Poll-kind: watermark dedupe strategy."""

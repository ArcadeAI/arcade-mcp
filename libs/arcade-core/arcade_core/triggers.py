"""Trigger-type declarations.

Toolkits declare trigger types as data; the worker serves them to the engine
alongside tool definitions. Validation is load-time: a broken declaration must
fail toolkit load, never reach the wire.
"""

from typing import Any, Literal

from jsonschema import exceptions as jsonschema_exceptions
from jsonschema.validators import validator_for
from pydantic import BaseModel, field_validator


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

    @field_validator("config_schema")
    @classmethod
    def _config_schema_is_valid_json_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        validator_class = validator_for(value)
        try:
            validator_class.check_schema(value)
        except jsonschema_exceptions.SchemaError as e:
            raise ValueError(f"not a valid JSON Schema: {e.message}") from e
        return value


def validate_trigger_types(trigger_types: list[TriggerType]) -> None:
    """Validate a toolkit's trigger-type declarations as a collection.

    Raises ValueError naming the offending slug so toolkit load fails fast.
    """
    seen: set[str] = set()
    for trigger_type in trigger_types:
        if trigger_type.slug in seen:
            raise ValueError(f"Duplicate trigger type slug: {trigger_type.slug}")
        seen.add(trigger_type.slug)

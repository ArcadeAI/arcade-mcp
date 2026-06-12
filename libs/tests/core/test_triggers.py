"""Trigger-type declaration model: load-time validation."""

import pytest
from arcade_core.triggers import TriggerType, validate_trigger_types
from pydantic import ValidationError


def valid_webhook_declaration() -> dict:
    return {
        "slug": "slack.message.received",
        "name": "Message received",
        "description": "Fires when a message arrives in a subscribed channel.",
        "kind": "webhook",
        "config_schema": {
            "type": "object",
            "properties": {"channel": {"type": "string"}},
            "required": ["channel"],
        },
        "payload_schema": {"type": "object"},
        "sample_payload": {"channel": "C123", "text": "hi"},
        "version": "1",
        "verification": {"scheme": "slack_v0"},
        "normalize_handler": "Slack.NormalizeMessageEvent",
    }


def test_missing_config_schema_fails_validation_naming_the_field():
    declaration = valid_webhook_declaration()
    del declaration["config_schema"]

    with pytest.raises(ValidationError) as exc_info:
        TriggerType.model_validate(declaration)

    assert "config_schema" in str(exc_info.value)


def test_duplicate_slug_within_a_toolkit_fails_validation_naming_the_slug():
    first = TriggerType.model_validate(valid_webhook_declaration())
    second = TriggerType.model_validate(valid_webhook_declaration())

    with pytest.raises(ValueError, match=r"slack\.message\.received"):
        validate_trigger_types([first, second])

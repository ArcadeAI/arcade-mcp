"""Request Body Schemas for API Tools

DO NOT EDIT THIS MODULE DIRECTLY.

THIS MODULE WAS AUTO-GENERATED AND CONTAINS OpenAPI REQUEST BODY SCHEMAS
FOR TOOLS WITH COMPLEX REQUEST BODIES. ANY CHANGES TO THIS MODULE WILL
BE OVERWRITTEN BY THE TRANSPILER.
"""

from typing import Any

REQUEST_BODY_SCHEMAS: dict[str, Any] = {
    "EXECUTETOOL": '{"required": ["tool_name"], "type": "object", "properties": {"include_error_stacktrace": {"type": "boolean", "description": "Whether to include the error stacktrace in the response. If not provided, the error stacktrace is not included."}, "input": {"type": "object", "description": "JSON input to the tool, if any", "allOf": [{"type": "object", "additionalProperties": true}]}, "run_at": {"type": "string", "description": "The time at which the tool should be run (optional). If not provided, the tool is run immediately. Format ISO 8601: YYYY-MM-DDTHH:MM:SS"}, "tool_name": {"type": "string"}, "tool_version": {"type": "string", "description": "The tool version to use (optional). If not provided, any version is used"}, "user_id": {"type": "string"}}}',  # noqa: E501
}

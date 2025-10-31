"""Request Body Schemas for API Tools

DO NOT EDIT THIS MODULE DIRECTLY.

THIS MODULE WAS AUTO-GENERATED AND CONTAINS OpenAPI REQUEST BODY SCHEMAS
FOR TOOLS WITH COMPLEX REQUEST BODIES. ANY CHANGES TO THIS MODULE WILL
BE OVERWRITTEN BY THE TRANSPILER.
"""

from typing import Any

REQUEST_BODY_SCHEMAS: dict[str, Any] = {
    "COMPLETEACTIONEXECUTION": '{"required": ["outputFields"], "type": "object", "properties": {"outputFields": {"type": "object", "additionalProperties": {"type": "string"}}}}',  # noqa: E501
    "COMPLETEBATCHACTIONEXECUTIONS": '{"required": ["inputs"], "type": "object", "properties": {"inputs": {"type": "array", "items": {"required": ["callbackId", "outputFields"], "type": "object", "properties": {"outputFields": {"type": "object", "additionalProperties": {"type": "string"}}, "callbackId": {"type": "string"}}}}}}',  # noqa: E501
    "GETWORKFLOWS": '{"required": ["inputs"], "type": "object", "properties": {"inputs": {"type": "array", "items": {"oneOf": [{"title": "FLOW_ID", "required": ["flowId", "type"], "type": "object", "properties": {"type": {"type": "string", "default": "FLOW_ID", "enum": ["FLOW_ID"]}, "flowId": {"type": "string"}}}]}}}}',  # noqa: E501
    "GETWORKFLOWIDMAPPINGS": '{"required": ["inputs"], "type": "object", "properties": {"inputs": {"type": "array", "items": {"oneOf": [{"title": "FLOW_ID", "required": ["flowMigrationStatuses", "type"], "type": "object", "properties": {"flowMigrationStatuses": {"type": "string"}, "type": {"type": "string", "default": "FLOW_ID", "enum": ["FLOW_ID"]}}}, {"title": "WORKFLOW_ID", "required": ["flowMigrationStatusForClassicWorkflows", "type"], "type": "object", "properties": {"flowMigrationStatusForClassicWorkflows": {"type": "string"}, "type": {"type": "string", "default": "WORKFLOW_ID", "enum": ["WORKFLOW_ID"]}}}]}}}}',  # noqa: E501
}

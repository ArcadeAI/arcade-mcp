"""Request Body Schemas for API Tools

DO NOT EDIT THIS MODULE DIRECTLY.

THIS MODULE WAS AUTO-GENERATED AND CONTAINS OpenAPI REQUEST BODY SCHEMAS
FOR TOOLS WITH COMPLEX REQUEST BODIES. ANY CHANGES TO THIS MODULE WILL
BE OVERWRITTEN BY THE TRANSPILER.
"""

from typing import Any

REQUEST_BODY_SCHEMAS: dict[str, Any] = {
    "ADDCOMMENTTOFIGMAFILE_REQUEST_BODY_SCHEMA": {
        "properties": {
            "client_meta": {
                "description": "The position where to place the comment.",
                "oneOf": [
                    {
                        "description": "A 2d vector.",
                        "properties": {
                            "x": {"description": "X coordinate of the vector.", "type": "number"},
                            "y": {"description": "Y coordinate of the vector.", "type": "number"},
                        },
                        "required": ["x", "y"],
                        "type": "object",
                    },
                    {
                        "description": "Position of a comment "
                        "relative to the frame to "
                        "which it is attached.",
                        "properties": {
                            "node_id": {
                                "description": "Unique id specifying the frame.",
                                "type": "string",
                            },
                            "node_offset": {
                                "description": "A 2d vector.",
                                "properties": {
                                    "x": {
                                        "description": "X coordinate of the vector.",
                                        "type": "number",
                                    },
                                    "y": {
                                        "description": "Y coordinate of the vector.",
                                        "type": "number",
                                    },
                                },
                                "required": ["x", "y"],
                                "type": "object",
                            },
                        },
                        "required": ["node_id", "node_offset"],
                        "type": "object",
                    },
                    {
                        "description": "Position of a region comment on the canvas.",
                        "properties": {
                            "comment_pin_corner": {
                                "default": "bottom-right",
                                "description": "The "
                                "corner "
                                "of "
                                "the "
                                "comment "
                                "region "
                                "to "
                                "pin "
                                "to "
                                "the "
                                "node's "
                                "corner "
                                "as "
                                "a "
                                "string "
                                "enum.",
                                "enum": ["top-left", "top-right", "bottom-left", "bottom-right"],
                                "type": "string",
                            },
                            "region_height": {
                                "description": "The "
                                "height "
                                "of "
                                "the "
                                "comment "
                                "region. "
                                "Must "
                                "be "
                                "greater "
                                "than "
                                "0.",
                                "type": "number",
                            },
                            "region_width": {
                                "description": "The "
                                "width "
                                "of "
                                "the "
                                "comment "
                                "region. "
                                "Must "
                                "be "
                                "greater "
                                "than "
                                "0.",
                                "type": "number",
                            },
                            "x": {"description": "X coordinate of the position.", "type": "number"},
                            "y": {"description": "Y coordinate of the position.", "type": "number"},
                        },
                        "required": ["x", "y", "region_height", "region_width"],
                        "type": "object",
                    },
                    {
                        "description": "Position of a region "
                        "comment relative to the "
                        "frame to which it is "
                        "attached.",
                        "properties": {
                            "comment_pin_corner": {
                                "default": "bottom-right",
                                "description": "The "
                                "corner "
                                "of "
                                "the "
                                "comment "
                                "region "
                                "to "
                                "pin "
                                "to "
                                "the "
                                "node's "
                                "corner "
                                "as "
                                "a "
                                "string "
                                "enum.",
                                "enum": ["top-left", "top-right", "bottom-left", "bottom-right"],
                                "type": "string",
                            },
                            "node_id": {
                                "description": "Unique id specifying the frame.",
                                "type": "string",
                            },
                            "node_offset": {
                                "description": "A 2d vector.",
                                "properties": {
                                    "x": {
                                        "description": "X coordinate of the vector.",
                                        "type": "number",
                                    },
                                    "y": {
                                        "description": "Y coordinate of the vector.",
                                        "type": "number",
                                    },
                                },
                                "required": ["x", "y"],
                                "type": "object",
                            },
                            "region_height": {
                                "description": "The "
                                "height "
                                "of "
                                "the "
                                "comment "
                                "region. "
                                "Must "
                                "be "
                                "greater "
                                "than "
                                "0.",
                                "type": "number",
                            },
                            "region_width": {
                                "description": "The "
                                "width "
                                "of "
                                "the "
                                "comment "
                                "region. "
                                "Must "
                                "be "
                                "greater "
                                "than "
                                "0.",
                                "type": "number",
                            },
                        },
                        "required": ["node_id", "node_offset", "region_height", "region_width"],
                        "type": "object",
                    },
                ],
            },
            "comment_id": {
                "description": "The ID of the comment to reply to, if "
                "any. This must be a root comment. You "
                "cannot reply to other replies (a "
                "comment that has a parent_id).",
                "type": "string",
            },
            "message": {
                "description": "The text contents of the comment to post.",
                "type": "string",
            },
        },
        "required": ["message"],
        "type": "object",
    },
    "ADDFIGMACOMMENTREACTION_REQUEST_BODY_SCHEMA": {
        "properties": {
            "emoji": {
                "description": "The emoji type of reaction as shortcode "
                "(e.g. `:heart:`, `:+1::skin-tone-2:`). The "
                "list of accepted emoji shortcodes can be "
                "found in [this "
                "file](https://raw.githubusercontent.com/missive/emoji-mart/main/packages/emoji-mart-data/sets/14/native.json) "  # noqa: E501
                "under the top-level emojis and aliases "
                "fields, with optional skin tone modifiers "
                "when applicable.",
                "type": "string",
            }
        },
        "required": ["emoji"],
        "type": "object",
    },
    "CREATEFIGMAWEBHOOK_REQUEST_BODY_SCHEMA": {
        "properties": {
            "context": {
                "description": "Context to create the webhook for. Must be "
                '"team", "project", or "file".',
                "type": "string",
            },
            "context_id": {
                "description": "The id of the context you want to receive updates about.",
                "type": "string",
            },
            "description": {
                "description": "User provided description or name for "
                "the webhook. Max length 150 "
                "characters.",
                "type": "string",
            },
            "endpoint": {
                "description": "The HTTP endpoint that will receive a "
                "POST request when the event triggers. Max "
                "length 2048 characters.",
                "type": "string",
            },
            "event_type": {
                "description": "An enum representing the possible "
                "events that a webhook can subscribe to",
                "enum": [
                    "PING",
                    "FILE_UPDATE",
                    "FILE_VERSION_UPDATE",
                    "FILE_DELETE",
                    "LIBRARY_PUBLISH",
                    "FILE_COMMENT",
                    "DEV_MODE_STATUS_UPDATE",
                ],
                "type": "string",
            },
            "passcode": {
                "description": "String that will be passed back to your "
                "webhook endpoint to verify that it is "
                "being called by Figma. Max length 100 "
                "characters.",
                "type": "string",
            },
            "status": {
                "description": "An enum representing the possible statuses "
                "you can set a webhook to:\n"
                "- `ACTIVE`: The webhook is healthy and "
                "receive all events\n"
                "- `PAUSED`: The webhook is paused and will "
                "not receive any events",
                "enum": ["ACTIVE", "PAUSED"],
                "type": "string",
            },
            "team_id": {
                "deprecated": True,
                "description": "Team id to receive updates about. This is "
                "deprecated, use 'context' and 'context_id' "
                "instead.",
                "type": "string",
            },
        },
        "required": ["event_type", "endpoint", "passcode", "context", "context_id"],
        "type": "object",
    },
    "UPDATEFIGMAWEBHOOK_REQUEST_BODY_SCHEMA": {
        "properties": {
            "description": {
                "description": "User provided description or name for "
                "the webhook. Max length 150 "
                "characters.",
                "type": "string",
            },
            "endpoint": {
                "description": "The HTTP endpoint that will receive a "
                "POST request when the event triggers. Max "
                "length 2048 characters.",
                "type": "string",
            },
            "event_type": {
                "description": "An enum representing the possible "
                "events that a webhook can subscribe to",
                "enum": [
                    "PING",
                    "FILE_UPDATE",
                    "FILE_VERSION_UPDATE",
                    "FILE_DELETE",
                    "LIBRARY_PUBLISH",
                    "FILE_COMMENT",
                    "DEV_MODE_STATUS_UPDATE",
                ],
                "type": "string",
            },
            "passcode": {
                "description": "String that will be passed back to your "
                "webhook endpoint to verify that it is "
                "being called by Figma. Max length 100 "
                "characters.",
                "type": "string",
            },
            "status": {
                "description": "An enum representing the possible statuses "
                "you can set a webhook to:\n"
                "- `ACTIVE`: The webhook is healthy and "
                "receive all events\n"
                "- `PAUSED`: The webhook is paused and will "
                "not receive any events",
                "enum": ["ACTIVE", "PAUSED"],
                "type": "string",
            },
        },
        "required": ["event_type", "team_id", "endpoint", "passcode"],
        "type": "object",
    },
    "MANAGEFIGMAVARIABLES_REQUEST_BODY_SCHEMA": {
        "minProperties": 1,
        "properties": {
            "variableCollections": {
                "description": "For creating, updating, and deleting variable collections.",
                "items": {
                    "discriminator": {
                        "mapping": {
                            "CREATE": "#/components/schemas/VariableCollectionCreate",
                            "DELETE": "#/components/schemas/VariableCollectionDelete",
                            "UPDATE": "#/components/schemas/VariableCollectionUpdate",
                        },
                        "propertyName": "action",
                    },
                    "oneOf": [
                        {
                            "description": "An object "
                            "that "
                            "contains "
                            "details "
                            "about "
                            "creating "
                            "a "
                            "`VariableCollection`.",
                            "properties": {
                                "action": {
                                    "description": "The "
                                    "action "
                                    "to "
                                    "perform "
                                    "for "
                                    "the "
                                    "variable "
                                    "collection.",
                                    "enum": ["CREATE"],
                                    "type": "string",
                                },
                                "hiddenFromPublishing": {
                                    "default": False,
                                    "description": "Whether "
                                    "this "
                                    "variable "
                                    "collection "
                                    "is "
                                    "hidden "
                                    "when "
                                    "publishing "
                                    "the "
                                    "current "
                                    "file "
                                    "as "
                                    "a "
                                    "library.",
                                    "type": "boolean",
                                },
                                "id": {
                                    "description": "A temporary id for this variable collection.",
                                    "type": "string",
                                },
                                "initialModeId": {
                                    "description": "The "
                                    "initial "
                                    "mode "
                                    "refers "
                                    "to "
                                    "the "
                                    "mode "
                                    "that "
                                    "is "
                                    "created "
                                    "by "
                                    "default. "
                                    "You "
                                    "can "
                                    "set "
                                    "a "
                                    "temporary "
                                    "id "
                                    "here, "
                                    "in "
                                    "order "
                                    "to "
                                    "reference "
                                    "this "
                                    "mode "
                                    "later "
                                    "in "
                                    "this "
                                    "request.",
                                    "type": "string",
                                },
                                "name": {
                                    "description": "The name of this variable collection.",
                                    "type": "string",
                                },
                            },
                            "required": ["action", "name"],
                            "type": "object",
                        },
                        {
                            "description": "An object "
                            "that "
                            "contains "
                            "details "
                            "about "
                            "updating "
                            "a "
                            "`VariableCollection`.",
                            "properties": {
                                "action": {
                                    "description": "The "
                                    "action "
                                    "to "
                                    "perform "
                                    "for "
                                    "the "
                                    "variable "
                                    "collection.",
                                    "enum": ["UPDATE"],
                                    "type": "string",
                                },
                                "hiddenFromPublishing": {
                                    "default": False,
                                    "description": "Whether "
                                    "this "
                                    "variable "
                                    "collection "
                                    "is "
                                    "hidden "
                                    "when "
                                    "publishing "
                                    "the "
                                    "current "
                                    "file "
                                    "as "
                                    "a "
                                    "library.",
                                    "type": "boolean",
                                },
                                "id": {
                                    "description": "The id of the variable collection to update.",
                                    "type": "string",
                                },
                                "name": {
                                    "description": "The name of this variable collection.",
                                    "type": "string",
                                },
                            },
                            "required": ["action", "id"],
                            "type": "object",
                        },
                        {
                            "description": "An object "
                            "that "
                            "contains "
                            "details "
                            "about "
                            "deleting "
                            "a "
                            "`VariableCollection`.",
                            "properties": {
                                "action": {
                                    "description": "The "
                                    "action "
                                    "to "
                                    "perform "
                                    "for "
                                    "the "
                                    "variable "
                                    "collection.",
                                    "enum": ["DELETE"],
                                    "type": "string",
                                },
                                "id": {
                                    "description": "The id of the variable collection to delete.",
                                    "type": "string",
                                },
                            },
                            "required": ["action", "id"],
                            "type": "object",
                        },
                    ],
                },
                "type": "array",
            },
            "variableModeValues": {
                "description": "For setting a specific value, given a variable and a mode.",
                "items": {
                    "description": "An object that "
                    "represents a value "
                    "for a given mode of a "
                    "variable. All "
                    "properties are "
                    "required.",
                    "properties": {
                        "modeId": {
                            "description": "Must "
                            "correspond "
                            "to "
                            "a "
                            "mode "
                            "in "
                            "the "
                            "variable "
                            "collection "
                            "that "
                            "contains "
                            "the "
                            "target "
                            "variable.",
                            "type": "string",
                        },
                        "value": {
                            "description": "The "
                            "value "
                            "for "
                            "the "
                            "variable. "
                            "The "
                            "value "
                            "must "
                            "match "
                            "the "
                            "variable's "
                            "type. "
                            "If "
                            "setting "
                            "to "
                            "a "
                            "variable "
                            "alias, "
                            "the "
                            "alias "
                            "must "
                            "resolve "
                            "to "
                            "this "
                            "type.",
                            "oneOf": [
                                {"type": "boolean"},
                                {"type": "number"},
                                {"type": "string"},
                                {
                                    "description": "An RGB color",
                                    "properties": {
                                        "b": {
                                            "description": "Blue channel value, between 0 and 1.",
                                            "maximum": 1,
                                            "minimum": 0,
                                            "type": "number",
                                        },
                                        "g": {
                                            "description": "Green channel value, between 0 and 1.",
                                            "maximum": 1,
                                            "minimum": 0,
                                            "type": "number",
                                        },
                                        "r": {
                                            "description": "Red channel value, between 0 and 1.",
                                            "maximum": 1,
                                            "minimum": 0,
                                            "type": "number",
                                        },
                                    },
                                    "required": ["r", "g", "b"],
                                    "type": "object",
                                },
                                {
                                    "description": "An RGBA color",
                                    "properties": {
                                        "a": {
                                            "description": "Alpha channel value, between 0 and 1.",
                                            "maximum": 1,
                                            "minimum": 0,
                                            "type": "number",
                                        },
                                        "b": {
                                            "description": "Blue channel value, between 0 and 1.",
                                            "maximum": 1,
                                            "minimum": 0,
                                            "type": "number",
                                        },
                                        "g": {
                                            "description": "Green channel value, between 0 and 1.",
                                            "maximum": 1,
                                            "minimum": 0,
                                            "type": "number",
                                        },
                                        "r": {
                                            "description": "Red channel value, between 0 and 1.",
                                            "maximum": 1,
                                            "minimum": 0,
                                            "type": "number",
                                        },
                                    },
                                    "required": ["r", "g", "b", "a"],
                                    "type": "object",
                                },
                                {
                                    "description": "Contains a variable alias",
                                    "properties": {
                                        "id": {
                                            "description": "The "
                                            "id "
                                            "of "
                                            "the "
                                            "variable "
                                            "that "
                                            "the "
                                            "current "
                                            "variable "
                                            "is "
                                            "aliased "
                                            "to. "
                                            "This "
                                            "variable "
                                            "can "
                                            "be "
                                            "a "
                                            "local "
                                            "or "
                                            "remote "
                                            "variable, "
                                            "and "
                                            "both "
                                            "can "
                                            "be "
                                            "retrieved "
                                            "via "
                                            "the "
                                            "GET "
                                            "/v1/files/:file_key/variables/local "
                                            "endpoint.",
                                            "type": "string",
                                        },
                                        "type": {"enum": ["VARIABLE_ALIAS"], "type": "string"},
                                    },
                                    "required": ["type", "id"],
                                    "type": "object",
                                },
                            ],
                        },
                        "variableId": {
                            "description": "The "
                            "target "
                            "variable. "
                            "You "
                            "can "
                            "use "
                            "the "
                            "temporary "
                            "id "
                            "of "
                            "a "
                            "variable.",
                            "type": "string",
                        },
                    },
                    "required": ["variableId", "modeId", "value"],
                    "type": "object",
                },
                "type": "array",
            },
            "variableModes": {
                "description": "For creating, updating, and deleting "
                "modes within variable collections.",
                "items": {
                    "discriminator": {
                        "mapping": {
                            "CREATE": "#/components/schemas/VariableModeCreate",
                            "DELETE": "#/components/schemas/VariableModeDelete",
                            "UPDATE": "#/components/schemas/VariableModeUpdate",
                        },
                        "propertyName": "action",
                    },
                    "oneOf": [
                        {
                            "description": "An object that "
                            "contains "
                            "details about "
                            "creating a "
                            "`VariableMode`.",
                            "properties": {
                                "action": {
                                    "description": "The action to perform for the variable mode.",
                                    "enum": ["CREATE"],
                                    "type": "string",
                                },
                                "id": {
                                    "description": "A temporary id for this variable mode.",
                                    "type": "string",
                                },
                                "name": {
                                    "description": "The name of this variable mode.",
                                    "type": "string",
                                },
                                "variableCollectionId": {
                                    "description": "The "
                                    "variable "
                                    "collection "
                                    "that "
                                    "will "
                                    "contain "
                                    "the "
                                    "mode. "
                                    "You "
                                    "can "
                                    "use "
                                    "the "
                                    "temporary "
                                    "id "
                                    "of "
                                    "a "
                                    "variable "
                                    "collection.",
                                    "type": "string",
                                },
                            },
                            "required": ["action", "name", "variableCollectionId"],
                            "type": "object",
                        },
                        {
                            "description": "An object that "
                            "contains "
                            "details about "
                            "updating a "
                            "`VariableMode`.",
                            "properties": {
                                "action": {
                                    "description": "The action to perform for the variable mode.",
                                    "enum": ["UPDATE"],
                                    "type": "string",
                                },
                                "id": {
                                    "description": "The id of the variable mode to update.",
                                    "type": "string",
                                },
                                "name": {
                                    "description": "The name of this variable mode.",
                                    "type": "string",
                                },
                                "variableCollectionId": {
                                    "description": "The "
                                    "variable "
                                    "collection "
                                    "that "
                                    "contains "
                                    "the "
                                    "mode.",
                                    "type": "string",
                                },
                            },
                            "required": ["action", "id", "variableCollectionId"],
                            "type": "object",
                        },
                        {
                            "description": "An object that "
                            "contains "
                            "details about "
                            "deleting a "
                            "`VariableMode`.",
                            "properties": {
                                "action": {
                                    "description": "The action to perform for the variable mode.",
                                    "enum": ["DELETE"],
                                    "type": "string",
                                },
                                "id": {
                                    "description": "The id of the variable mode to delete.",
                                    "type": "string",
                                },
                            },
                            "required": ["action", "id"],
                            "type": "object",
                        },
                    ],
                },
                "type": "array",
            },
            "variables": {
                "description": "For creating, updating, and deleting variables.",
                "items": {
                    "discriminator": {
                        "mapping": {
                            "CREATE": "#/components/schemas/VariableCreate",
                            "DELETE": "#/components/schemas/VariableDelete",
                            "UPDATE": "#/components/schemas/VariableUpdate",
                        },
                        "propertyName": "action",
                    },
                    "oneOf": [
                        {
                            "description": "An object that "
                            "contains details "
                            "about creating a "
                            "`Variable`.",
                            "properties": {
                                "action": {
                                    "description": "The action to perform for the variable.",
                                    "enum": ["CREATE"],
                                    "type": "string",
                                },
                                "codeSyntax": {
                                    "description": "An "
                                    "object "
                                    "containing "
                                    "platform-specific "
                                    "code "
                                    "syntax "
                                    "definitions "
                                    "for "
                                    "a "
                                    "variable. "
                                    "All "
                                    "platforms "
                                    "are "
                                    "optional.",
                                    "properties": {
                                        "ANDROID": {"type": "string"},
                                        "WEB": {"type": "string"},
                                        "iOS": {"type": "string"},
                                    },
                                    "type": "object",
                                },
                                "description": {
                                    "description": "The description of this variable.",
                                    "type": "string",
                                },
                                "hiddenFromPublishing": {
                                    "default": False,
                                    "description": "Whether "
                                    "this "
                                    "variable "
                                    "is "
                                    "hidden "
                                    "when "
                                    "publishing "
                                    "the "
                                    "current "
                                    "file "
                                    "as "
                                    "a "
                                    "library.",
                                    "type": "boolean",
                                },
                                "id": {
                                    "description": "A temporary id for this variable.",
                                    "type": "string",
                                },
                                "name": {
                                    "description": "The name of this variable.",
                                    "type": "string",
                                },
                                "resolvedType": {
                                    "description": "Defines "
                                    "the "
                                    "types "
                                    "of "
                                    "data "
                                    "a "
                                    "VariableData "
                                    "object "
                                    "can "
                                    "eventually "
                                    "equal",
                                    "enum": ["BOOLEAN", "FLOAT", "STRING", "COLOR"],
                                    "type": "string",
                                },
                                "scopes": {
                                    "description": "An "
                                    "array "
                                    "of "
                                    "scopes "
                                    "in "
                                    "the "
                                    "UI "
                                    "where "
                                    "this "
                                    "variable "
                                    "is "
                                    "shown. "
                                    "Setting "
                                    "this "
                                    "property "
                                    "will "
                                    "show/hide "
                                    "this "
                                    "variable "
                                    "in "
                                    "the "
                                    "variable "
                                    "picker "
                                    "UI "
                                    "for "
                                    "different "
                                    "fields.",
                                    "items": {
                                        "description": "Scopes "
                                        "allow "
                                        "a "
                                        "variable "
                                        "to "
                                        "be "
                                        "shown "
                                        "or "
                                        "hidden "
                                        "in "
                                        "the "
                                        "variable "
                                        "picker "
                                        "for "
                                        "various "
                                        "fields. "
                                        "This "
                                        "declutters "
                                        "the "
                                        "Figma "
                                        "UI "
                                        "if "
                                        "you "
                                        "have "
                                        "a "
                                        "large "
                                        "number "
                                        "of "
                                        "variables. "
                                        "Variable "
                                        "scopes "
                                        "are "
                                        "currently "
                                        "supported "
                                        "on "
                                        "`FLOAT`, "
                                        "`STRING`, "
                                        "and "
                                        "`COLOR` "
                                        "variables.\n"
                                        "\n"
                                        "`ALL_SCOPES` "
                                        "is "
                                        "a "
                                        "special "
                                        "scope "
                                        "that "
                                        "means "
                                        "that "
                                        "the "
                                        "variable "
                                        "will "
                                        "be "
                                        "shown "
                                        "in "
                                        "the "
                                        "variable "
                                        "picker "
                                        "for "
                                        "all "
                                        "variable "
                                        "fields. "
                                        "If "
                                        "`ALL_SCOPES` "
                                        "is "
                                        "set, "
                                        "no "
                                        "additional "
                                        "scopes "
                                        "can "
                                        "be "
                                        "set.\n"
                                        "\n"
                                        "`ALL_FILLS` "
                                        "is "
                                        "a "
                                        "special "
                                        "scope "
                                        "that "
                                        "means "
                                        "that "
                                        "the "
                                        "variable "
                                        "will "
                                        "be "
                                        "shown "
                                        "in "
                                        "the "
                                        "variable "
                                        "picker "
                                        "for "
                                        "all "
                                        "fill "
                                        "fields. "
                                        "If "
                                        "`ALL_FILLS` "
                                        "is "
                                        "set, "
                                        "no "
                                        "additional "
                                        "fill "
                                        "scopes "
                                        "can "
                                        "be "
                                        "set.\n"
                                        "\n"
                                        "Valid "
                                        "scopes "
                                        "for "
                                        "`FLOAT` "
                                        "variables:\n"
                                        "- "
                                        "`ALL_SCOPES`\n"
                                        "- "
                                        "`TEXT_CONTENT`\n"
                                        "- "
                                        "`WIDTH_HEIGHT`\n"
                                        "- "
                                        "`GAP`\n"
                                        "- "
                                        "`STROKE_FLOAT`\n"
                                        "- "
                                        "`EFFECT_FLOAT`\n"
                                        "- "
                                        "`OPACITY`\n"
                                        "- "
                                        "`FONT_WEIGHT`\n"
                                        "- "
                                        "`FONT_SIZE`\n"
                                        "- "
                                        "`LINE_HEIGHT`\n"
                                        "- "
                                        "`LETTER_SPACING`\n"
                                        "- "
                                        "`PARAGRAPH_SPACING`\n"
                                        "- "
                                        "`PARAGRAPH_INDENT`\n"
                                        "\n"
                                        "Valid "
                                        "scopes "
                                        "for "
                                        "`STRING` "
                                        "variables:\n"
                                        "- "
                                        "`ALL_SCOPES`\n"
                                        "- "
                                        "`TEXT_CONTENT`\n"
                                        "- "
                                        "`FONT_FAMILY`\n"
                                        "- "
                                        "`FONT_STYLE`\n"
                                        "\n"
                                        "Valid "
                                        "scopes "
                                        "for "
                                        "`COLOR` "
                                        "variables:\n"
                                        "- "
                                        "`ALL_SCOPES`\n"
                                        "- "
                                        "`ALL_FILLS`\n"
                                        "- "
                                        "`FRAME_FILL`\n"
                                        "- "
                                        "`SHAPE_FILL`\n"
                                        "- "
                                        "`TEXT_FILL`\n"
                                        "- "
                                        "`STROKE_COLOR`\n"
                                        "- "
                                        "`EFFECT_COLOR`",
                                        "enum": [
                                            "ALL_SCOPES",
                                            "TEXT_CONTENT",
                                            "CORNER_RADIUS",
                                            "WIDTH_HEIGHT",
                                            "GAP",
                                            "ALL_FILLS",
                                            "FRAME_FILL",
                                            "SHAPE_FILL",
                                            "TEXT_FILL",
                                            "STROKE_COLOR",
                                            "STROKE_FLOAT",
                                            "EFFECT_FLOAT",
                                            "EFFECT_COLOR",
                                            "OPACITY",
                                            "FONT_FAMILY",
                                            "FONT_STYLE",
                                            "FONT_WEIGHT",
                                            "FONT_SIZE",
                                            "LINE_HEIGHT",
                                            "LETTER_SPACING",
                                            "PARAGRAPH_SPACING",
                                            "PARAGRAPH_INDENT",
                                            "FONT_VARIATIONS",
                                        ],
                                        "type": "string",
                                    },
                                    "type": "array",
                                },
                                "variableCollectionId": {
                                    "description": "The "
                                    "variable "
                                    "collection "
                                    "that "
                                    "will "
                                    "contain "
                                    "the "
                                    "variable. "
                                    "You "
                                    "can "
                                    "use "
                                    "the "
                                    "temporary "
                                    "id "
                                    "of "
                                    "a "
                                    "variable "
                                    "collection.",
                                    "type": "string",
                                },
                            },
                            "required": ["action", "name", "variableCollectionId", "resolvedType"],
                            "type": "object",
                        },
                        {
                            "description": "An object that "
                            "contains details "
                            "about updating a "
                            "`Variable`.",
                            "properties": {
                                "action": {
                                    "description": "The action to perform for the variable.",
                                    "enum": ["UPDATE"],
                                    "type": "string",
                                },
                                "codeSyntax": {
                                    "description": "An "
                                    "object "
                                    "containing "
                                    "platform-specific "
                                    "code "
                                    "syntax "
                                    "definitions "
                                    "for "
                                    "a "
                                    "variable. "
                                    "All "
                                    "platforms "
                                    "are "
                                    "optional.",
                                    "properties": {
                                        "ANDROID": {"type": "string"},
                                        "WEB": {"type": "string"},
                                        "iOS": {"type": "string"},
                                    },
                                    "type": "object",
                                },
                                "description": {
                                    "description": "The description of this variable.",
                                    "type": "string",
                                },
                                "hiddenFromPublishing": {
                                    "default": False,
                                    "description": "Whether "
                                    "this "
                                    "variable "
                                    "is "
                                    "hidden "
                                    "when "
                                    "publishing "
                                    "the "
                                    "current "
                                    "file "
                                    "as "
                                    "a "
                                    "library.",
                                    "type": "boolean",
                                },
                                "id": {
                                    "description": "The id of the variable to update.",
                                    "type": "string",
                                },
                                "name": {
                                    "description": "The name of this variable.",
                                    "type": "string",
                                },
                                "scopes": {
                                    "description": "An "
                                    "array "
                                    "of "
                                    "scopes "
                                    "in "
                                    "the "
                                    "UI "
                                    "where "
                                    "this "
                                    "variable "
                                    "is "
                                    "shown. "
                                    "Setting "
                                    "this "
                                    "property "
                                    "will "
                                    "show/hide "
                                    "this "
                                    "variable "
                                    "in "
                                    "the "
                                    "variable "
                                    "picker "
                                    "UI "
                                    "for "
                                    "different "
                                    "fields.",
                                    "items": {
                                        "description": "Scopes "
                                        "allow "
                                        "a "
                                        "variable "
                                        "to "
                                        "be "
                                        "shown "
                                        "or "
                                        "hidden "
                                        "in "
                                        "the "
                                        "variable "
                                        "picker "
                                        "for "
                                        "various "
                                        "fields. "
                                        "This "
                                        "declutters "
                                        "the "
                                        "Figma "
                                        "UI "
                                        "if "
                                        "you "
                                        "have "
                                        "a "
                                        "large "
                                        "number "
                                        "of "
                                        "variables. "
                                        "Variable "
                                        "scopes "
                                        "are "
                                        "currently "
                                        "supported "
                                        "on "
                                        "`FLOAT`, "
                                        "`STRING`, "
                                        "and "
                                        "`COLOR` "
                                        "variables.\n"
                                        "\n"
                                        "`ALL_SCOPES` "
                                        "is "
                                        "a "
                                        "special "
                                        "scope "
                                        "that "
                                        "means "
                                        "that "
                                        "the "
                                        "variable "
                                        "will "
                                        "be "
                                        "shown "
                                        "in "
                                        "the "
                                        "variable "
                                        "picker "
                                        "for "
                                        "all "
                                        "variable "
                                        "fields. "
                                        "If "
                                        "`ALL_SCOPES` "
                                        "is "
                                        "set, "
                                        "no "
                                        "additional "
                                        "scopes "
                                        "can "
                                        "be "
                                        "set.\n"
                                        "\n"
                                        "`ALL_FILLS` "
                                        "is "
                                        "a "
                                        "special "
                                        "scope "
                                        "that "
                                        "means "
                                        "that "
                                        "the "
                                        "variable "
                                        "will "
                                        "be "
                                        "shown "
                                        "in "
                                        "the "
                                        "variable "
                                        "picker "
                                        "for "
                                        "all "
                                        "fill "
                                        "fields. "
                                        "If "
                                        "`ALL_FILLS` "
                                        "is "
                                        "set, "
                                        "no "
                                        "additional "
                                        "fill "
                                        "scopes "
                                        "can "
                                        "be "
                                        "set.\n"
                                        "\n"
                                        "Valid "
                                        "scopes "
                                        "for "
                                        "`FLOAT` "
                                        "variables:\n"
                                        "- "
                                        "`ALL_SCOPES`\n"
                                        "- "
                                        "`TEXT_CONTENT`\n"
                                        "- "
                                        "`WIDTH_HEIGHT`\n"
                                        "- "
                                        "`GAP`\n"
                                        "- "
                                        "`STROKE_FLOAT`\n"
                                        "- "
                                        "`EFFECT_FLOAT`\n"
                                        "- "
                                        "`OPACITY`\n"
                                        "- "
                                        "`FONT_WEIGHT`\n"
                                        "- "
                                        "`FONT_SIZE`\n"
                                        "- "
                                        "`LINE_HEIGHT`\n"
                                        "- "
                                        "`LETTER_SPACING`\n"
                                        "- "
                                        "`PARAGRAPH_SPACING`\n"
                                        "- "
                                        "`PARAGRAPH_INDENT`\n"
                                        "\n"
                                        "Valid "
                                        "scopes "
                                        "for "
                                        "`STRING` "
                                        "variables:\n"
                                        "- "
                                        "`ALL_SCOPES`\n"
                                        "- "
                                        "`TEXT_CONTENT`\n"
                                        "- "
                                        "`FONT_FAMILY`\n"
                                        "- "
                                        "`FONT_STYLE`\n"
                                        "\n"
                                        "Valid "
                                        "scopes "
                                        "for "
                                        "`COLOR` "
                                        "variables:\n"
                                        "- "
                                        "`ALL_SCOPES`\n"
                                        "- "
                                        "`ALL_FILLS`\n"
                                        "- "
                                        "`FRAME_FILL`\n"
                                        "- "
                                        "`SHAPE_FILL`\n"
                                        "- "
                                        "`TEXT_FILL`\n"
                                        "- "
                                        "`STROKE_COLOR`\n"
                                        "- "
                                        "`EFFECT_COLOR`",
                                        "enum": [
                                            "ALL_SCOPES",
                                            "TEXT_CONTENT",
                                            "CORNER_RADIUS",
                                            "WIDTH_HEIGHT",
                                            "GAP",
                                            "ALL_FILLS",
                                            "FRAME_FILL",
                                            "SHAPE_FILL",
                                            "TEXT_FILL",
                                            "STROKE_COLOR",
                                            "STROKE_FLOAT",
                                            "EFFECT_FLOAT",
                                            "EFFECT_COLOR",
                                            "OPACITY",
                                            "FONT_FAMILY",
                                            "FONT_STYLE",
                                            "FONT_WEIGHT",
                                            "FONT_SIZE",
                                            "LINE_HEIGHT",
                                            "LETTER_SPACING",
                                            "PARAGRAPH_SPACING",
                                            "PARAGRAPH_INDENT",
                                            "FONT_VARIATIONS",
                                        ],
                                        "type": "string",
                                    },
                                    "type": "array",
                                },
                            },
                            "required": ["action", "id"],
                            "type": "object",
                        },
                        {
                            "description": "An object that "
                            "contains details "
                            "about deleting a "
                            "`Variable`.",
                            "properties": {
                                "action": {
                                    "description": "The action to perform for the variable.",
                                    "enum": ["DELETE"],
                                    "type": "string",
                                },
                                "id": {
                                    "description": "The id of the variable to delete.",
                                    "type": "string",
                                },
                            },
                            "required": ["action", "id"],
                            "type": "object",
                        },
                    ],
                },
                "type": "array",
            },
        },
        "type": "object",
    },
    "CREATEBULKDEVRESOURCES_REQUEST_BODY_SCHEMA": {
        "properties": {
            "dev_resources": {
                "description": "An array of dev resources.",
                "items": {
                    "properties": {
                        "file_key": {
                            "description": "The file key where the dev resource belongs.",
                            "type": "string",
                        },
                        "name": {"description": "The name of the dev resource.", "type": "string"},
                        "node_id": {
                            "description": "The target node to attach the dev resource to.",
                            "type": "string",
                        },
                        "url": {"description": "The URL of the dev resource.", "type": "string"},
                    },
                    "required": ["name", "url", "file_key", "node_id"],
                    "type": "object",
                },
                "type": "array",
            }
        },
        "required": ["dev_resources"],
        "type": "object",
    },
    "BULKUPDATEFIGMADEVRESOURCES_REQUEST_BODY_SCHEMA": {
        "properties": {
            "dev_resources": {
                "description": "An array of dev resources.",
                "items": {
                    "properties": {
                        "id": {
                            "description": "Unique identifier of the dev resource",
                            "type": "string",
                        },
                        "name": {"description": "The name of the dev resource.", "type": "string"},
                        "url": {"description": "The URL of the dev resource.", "type": "string"},
                    },
                    "required": ["id"],
                    "type": "object",
                },
                "type": "array",
            }
        },
        "required": ["dev_resources"],
        "type": "object",
    },
}

"""Request Body Schemas for API Tools

DO NOT EDIT THIS MODULE DIRECTLY.

THIS MODULE WAS AUTO-GENERATED AND CONTAINS OpenAPI REQUEST BODY SCHEMAS
FOR TOOLS WITH COMPLEX REQUEST BODIES. ANY CHANGES TO THIS MODULE WILL
BE OVERWRITTEN BY THE TRANSPILER.
"""

from typing import Any

REQUEST_BODY_SCHEMAS: dict[str, Any] = {
    "UPDATEZOHOCREATORREPORTRECORDS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "criteria": {
                "example": '(Single_Line.contains("Single Line of Text"))',
                "type": "string",
            },
            "data": {
                "example": '{"Email":"jake@zylker.com","Phone_Number":"+15876786783"}',
                "type": "object",
            },
            "result": {
                "properties": {
                    "fields": {
                        "example": '["Phone_Number","Email"]',
                        "items": {"type": "string"},
                        "type": "array",
                    },
                    "message": {"example": True, "type": "boolean"},
                    "tasks": {"example": True, "type": "boolean"},
                },
                "type": "object",
            },
        },
        "type": "object",
    },
    "DELETEREPORTRECORDS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "criteria": {
                "example": '(Single_Line.contains("Single Line of Text"))',
                "type": "string",
            },
            "result": {
                "properties": {
                    "message": {"example": True, "type": "boolean"},
                    "tasks": {"example": True, "type": "boolean"},
                },
                "type": "object",
            },
        },
        "type": "object",
    },
    "INSERTRECORDSINZOHOFORM_REQUEST_BODY_SCHEMA": {
        "properties": {
            "data": {
                "example": (
                    '[{"Email":"jason@zylker.com","Phone_Number":"+16103948336"},'
                    '{"Email":"p.boyle@zylker.com","Phone_Number":"+12096173907"}]'
                ),
                "items": {"type": "object"},
                "type": "array",
            },
            "result": {
                "properties": {
                    "fields": {
                        "example": '["Phone_Number","Email"]',
                        "items": {"type": "string"},
                        "type": "array",
                    },
                    "message": {"example": True, "type": "boolean"},
                    "tasks": {"example": True, "type": "boolean"},
                },
                "type": "object",
            },
        },
        "type": "object",
    },
    "UPDATEZOHORECORD_REQUEST_BODY_SCHEMA": {
        "properties": {
            "data": {
                "example": '{"Email":"jake@zylker.com","Phone_Number":"+15876786783"}',
                "type": "object",
            },
            "result": {
                "properties": {
                    "fields": {
                        "example": '["Phone_Number","Email"]',
                        "items": {"type": "string"},
                        "type": "array",
                    },
                    "message": {"example": True, "type": "boolean"},
                    "tasks": {"example": True, "type": "boolean"},
                },
                "type": "object",
            },
        },
        "type": "object",
    },
    "DELETEZOHORECORD_REQUEST_BODY_SCHEMA": {
        "properties": {
            "result": {
                "properties": {
                    "message": {"example": True, "type": "boolean"},
                    "tasks": {"example": True, "type": "boolean"},
                },
                "type": "object",
            }
        },
        "type": "object",
    },
    "CREATEBULKREADJOB_REQUEST_BODY_SCHEMA": {
        "properties": {
            "query": {
                "properties": {
                    "criteria": {"example": "Number==1", "type": "string"},
                    "fields": {
                        "example": '["Number","Single_Line","Radio","Date","Checkbox"]',
                        "items": {"type": "string"},
                        "type": "array",
                    },
                    "max_records": {
                        "example": 150000,
                        "format": "int64",
                        "maximum": 200000,
                        "minimum": 100000,
                        "type": "integer",
                    },
                },
                "type": "object",
            }
        },
        "type": "object",
    },
    "ADDRECORDSTOZOHOFORM_REQUEST_BODY_SCHEMA": {
        "properties": {
            "data": {
                "example": (
                    '[{"Email":"jason@zylker.com","Phone_Number":"+16103948336"},'
                    '{"Email":"p.boyle@zylker.com","Phone_Number":"+12096173907"}]'
                ),
                "items": {"type": "object"},
                "type": "array",
            },
            "result": {
                "properties": {
                    "fields": {
                        "example": '["Phone_Number","Email"]',
                        "items": {"type": "string"},
                        "type": "array",
                    },
                    "message": {"example": True, "type": "boolean"},
                    "tasks": {"example": True, "type": "boolean"},
                },
                "type": "object",
            },
        },
        "type": "object",
    },
}

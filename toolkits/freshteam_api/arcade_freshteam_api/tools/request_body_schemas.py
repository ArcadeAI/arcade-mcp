"""Request Body Schemas for API Tools

DO NOT EDIT THIS MODULE DIRECTLY.

THIS MODULE WAS AUTO-GENERATED AND CONTAINS OpenAPI REQUEST BODY SCHEMAS
FOR TOOLS WITH COMPLEX REQUEST BODIES. ANY CHANGES TO THIS MODULE WILL
BE OVERWRITTEN BY THE TRANSPILER.
"""

from typing import Any

REQUEST_BODY_SCHEMAS: dict[str, Any] = {
    "ADDNEWEMPLOYEE_REQUEST_BODY_SCHEMA": {},
    "UPDATEEMPLOYEEINFO_REQUEST_BODY_SCHEMA": {},
    "CREATENEWHIRE_REQUEST_BODY_SCHEMA": {},
    "UPDATENEWHIREINFO_REQUEST_BODY_SCHEMA": {},
    "ADDJOBAPPLICANT_REQUEST_BODY_SCHEMA": {},
    "UPDATECANDIDATEDETAILS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "cover_letters": {
                "items": {"example": "\\x00\\x00\\x00\\x02", "format": "binary", "type": "string"},
                "type": "array",
            },
            "created_at": {"format": "date", "type": "string"},
            "date_of_birth": {"format": "date", "type": "string"},
            "deleted": {"example": False, "type": "boolean"},
            "description": {"example": "sample-description", "type": "string"},
            "email": {"example": "email@example.com", "type": "string"},
            "first_name": {"example": "Jane", "type": "string"},
            "gender": {"enum": ["male", "female"], "example": "female", "type": "string"},
            "id": {"example": 96535, "format": "int64", "type": "integer"},
            "last_name": {"example": "Sloan", "type": "string"},
            "location": {
                "properties": {
                    "city": {"example": "encoding", "type": "string"},
                    "country_code": {"example": "Ridges", "type": "string"},
                    "state": {"example": "Riel", "type": "string"},
                    "street": {"example": "payment", "type": "string"},
                    "zip_code": {"example": "Seychelles", "type": "string"},
                },
                "type": "object",
            },
            "middle_name": {"example": "S", "type": "string"},
            "mobile": {"example": "SDD", "type": "string"},
            "owner_id": {"example": 51327, "format": "int64", "type": "integer"},
            "phone": {"example": "HTTP", "type": "string"},
            "portfolios": {
                "items": {"example": "\\x00\\x00\\x00\\x02", "format": "binary", "type": "string"},
                "type": "array",
            },
            "positions": {
                "items": {
                    "properties": {
                        "company": {"example": "encoding", "type": "string"},
                        "end_date": {
                            "example": "2019-09-25T15:52:15.110Z",
                            "format": "date",
                            "type": "object",
                        },
                        "is_current": {"example": True, "type": "boolean"},
                        "start_date": {
                            "example": "2019-09-25T15:52:15.110Z",
                            "format": "date",
                            "type": "object",
                        },
                        "summary": {"example": "payment", "type": "string"},
                        "title": {"example": "Riel", "type": "string"},
                    },
                    "type": "object",
                },
                "type": "array",
            },
            "profile_links": {
                "items": {
                    "properties": {
                        "name": {"example": "payment", "type": "string"},
                        "url": {"example": "New", "type": "string"},
                    },
                    "type": "object",
                },
                "type": "array",
            },
            "qualifications": {
                "items": {
                    "properties": {
                        "degree": {"example": "payment", "type": "string"},
                        "end_date": {
                            "example": "2019-09-25T15:52:15.110Z",
                            "format": "date",
                            "type": "object",
                        },
                        "field_of_study": {"example": "Riel", "type": "string"},
                        "grade": {"example": "payment", "type": "string"},
                        "is_current": {"example": True, "type": "boolean"},
                        "school_name": {"example": "encoding", "type": "string"},
                        "start_date": {
                            "example": "2019-09-25T15:52:15.110Z",
                            "format": "date",
                            "type": "object",
                        },
                        "summary": {"example": "payment", "type": "string"},
                    },
                    "type": "object",
                },
                "type": "array",
            },
            "resumes": {
                "items": {"example": "\\x00\\x00\\x00\\x02", "format": "binary", "type": "string"},
                "type": "array",
            },
            "skills": {"example": ["abc", "def"], "items": {"type": "string"}, "type": "array"},
            "skype_id": {"example": "value-added", "type": "string"},
            "source_category_id": {"example": 81910, "format": "int64", "type": "integer"},
            "source_id": {"example": 51339, "format": "int64", "type": "integer"},
            "spam": {"example": False, "type": "boolean"},
            "tags": {"example": ["abc", "def"], "items": {"type": "string"}, "type": "array"},
            "total_experience_in_months": {"example": 51339, "format": "int64", "type": "integer"},
            "updated_at": {"format": "date", "type": "string"},
        },
        "required": ["email", "first_name", "last_name", "source_category_id", "source_id"],
        "type": "object",
    },
}

from typing import ClassVar, Union

from pydantic import BaseModel


class ToolVersion(BaseModel):
    name: str
    version: str


class ToolAuthorizationContext(BaseModel):
    token: str | None = None


class ToolContext(BaseModel):
    authorization: ToolAuthorizationContext | None = None


class InvokeToolRequest(BaseModel):
    run_id: str
    invocation_id: str
    created_at: str
    tool: ToolVersion
    inputs: dict | None
    context: ToolContext


class ToolOutputError(BaseModel):
    message: str
    developer_message: str | None = None


class ToolOutput(BaseModel):
    value: Union[str, int, float, bool, dict] | None = None
    error: ToolOutputError | None = None

    class Config:
        json_schema_extra: ClassVar[dict] = {
            "oneOf": [
                {"required": ["value"]},
                {"required": ["error"]},
                {"required": ["requires_authorization"]},
                {"required": ["artifact"]},
            ]
        }


class InvokeToolResponse(BaseModel):
    invocation_id: str
    finished_at: str
    duration: float
    success: bool
    output: ToolOutput | None = None

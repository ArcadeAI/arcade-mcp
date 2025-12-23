from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DatacacheSetResult(BaseModel):
    table: str
    id: str
    action: Literal["inserted", "updated"]
    record: dict[str, Any] | None = None
    created_at: int = Field(..., ge=0)
    updated_at: int = Field(..., ge=0)
    bytes_saved: int = Field(..., ge=0)

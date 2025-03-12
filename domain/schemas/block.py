# domain/schemas/block.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class BlockCreate(BaseModel):
    blocked_id: str = Field(..., description="ID of the user or vendor being blocked as a string")
    reason: Optional[str] = Field(None, description="Optional reason for the block")

    @field_validator("blocked_id", mode="before")
    def validate_blocked_id(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Blocked ID must be a non-empty string")
        return value

    @field_validator("reason")
    def validate_reason(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Reason must be a non-empty string if provided")
        return value


class BlockResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the block as a string")
    blocker_id: str = Field(..., description="ID of the user or vendor who initiated the block as a string")
    blocked_id: str = Field(..., description="ID of the user or vendor being blocked as a string")
    reason: Optional[str] = Field(None, description="Reason for the block")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

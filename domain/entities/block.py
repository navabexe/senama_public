# domain/entities/block.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class Block(BaseModel):
    """Entity representing a block relationship between users or vendors."""
    id: Optional[str] = Field(None, description="Unique identifier of the block as a string")
    blocker_id: str = Field(..., description="ID of the user or vendor who initiated the block as a string")
    blocked_id: str = Field(..., description="ID of the user or vendor being blocked as a string")
    reason: Optional[str] = Field(None, description="Optional reason for the block")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @field_validator("id", "blocker_id", "blocked_id", mode="before")
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @field_validator("blocker_id")
    def prevent_cls_block(cls, value, values):
        """Ensure blocker_id is not the same as blocked_id."""
        if "blocked_id" in values and value == values["blocked_id"]:
            raise ValueError("blocker_id cannot be the same as blocked_id")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

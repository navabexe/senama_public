# domain/entities/collaboration.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class Collaboration(BaseModel):
    """Entity representing a collaboration request between vendors."""
    id: Optional[str] = Field(None, description="Unique identifier of the collaboration as a string")
    requester_vendor_id: str = Field(..., description="ID of the vendor requesting the collaboration as a string")
    target_vendor_id: str = Field(..., description="ID of the target vendor as a string")
    product_id: str = Field(..., description="ID of the product involved in the collaboration as a string")
    status: str = Field("pending", description="Status of the collaboration (pending/accepted/rejected)")
    message: Optional[str] = Field(None, description="Optional message accompanying the collaboration request")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @field_validator("id", "requester_vendor_id", "target_vendor_id", "product_id", mode="before")
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @field_validator("requester_vendor_id")
    def prevent_cls_collaboration(cls, value, values):
        """Ensure requester_vendor_id is not the same as target_vendor_id."""
        if "target_vendor_id" in values and value == values["target_vendor_id"]:
            raise ValueError("requester_vendor_id cannot be the same as target_vendor_id")
        return value

    @field_validator("status")
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ["pending", "accepted", "rejected"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

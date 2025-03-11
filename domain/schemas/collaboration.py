# domain/schemas/collaboration.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class CollaborationCreate(BaseModel):
    target_vendor_id: str = Field(..., description="ID of the target vendor as a string")
    product_id: str = Field(..., description="ID of the product involved as a string")
    message: Optional[str] = Field(None, description="Optional message for the collaboration request")

    @validator("target_vendor_id", "product_id", pre=True)
    def validate_id_format(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ID must be a non-empty string")
        return value

    @validator("message")
    def validate_message(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Message must be a non-empty string if provided")
        return value


class CollaborationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated status of the collaboration")

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["pending", "accepted", "rejected"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value


class CollaborationResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the collaboration as a string")
    requester_vendor_id: str = Field(..., description="ID of the requesting vendor as a string")
    target_vendor_id: str = Field(..., description="ID of the target vendor as a string")
    product_id: str = Field(..., description="ID of the product involved as a string")
    status: str = Field(..., description="Status of the collaboration")
    message: Optional[str] = Field(None, description="Message for the collaboration request")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

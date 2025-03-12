# domain/schemas/notification.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class NotificationCreate(BaseModel):
    user_id: Optional[str] = Field(None, description="ID of the user receiving the notification as a string")
    vendor_id: Optional[str] = Field(None, description="ID of the vendor receiving the notification as a string")
    type: str = Field(..., description="Type of notification (order/story/system)")
    message: str = Field(..., description="Message content of the notification")
    related_id: Optional[str] = Field(None, description="ID of the related entity as a string")

    @field_validator("user_id", "vendor_id", "related_id", mode="before")
    def validate_id_format(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("ID must be a non-empty string if provided")
        return value

    @field_validator("user_id", "vendor_id")
    def ensure_at_least_one_recipient(cls, value, values):
        if "user_id" in values and "vendor_id" in values:
            if values["user_id"] is None and value is None:
                raise ValueError("At least one of user_id or vendor_id must be provided")
        return value

    @field_validator("type")
    def validate_type(cls, value):
        valid_types = ["order", "story", "system"]
        if value not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}")
        return value

    @field_validator("message")
    def validate_message(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Message must be a non-empty string")
        return value.strip()


class NotificationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated status of the notification")

    @field_validator("status")
    def validate_status(cls, value):
        valid_statuses = ["unread", "read"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value


class NotificationResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the notification as a string")
    user_id: Optional[str] = Field(None, description="ID of the user receiving the notification as a string")
    vendor_id: Optional[str] = Field(None, description="ID of the vendor receiving the notification as a string")
    type: str = Field(..., description="Type of notification")
    message: str = Field(..., description="Message content of the notification")
    status: str = Field(..., description="Status of the notification")
    related_id: Optional[str] = Field(None, description="ID of the related entity as a string")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# domain/entities/notification.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class Notification(BaseModel):
    """Entity representing a notification in the marketplace."""
    id: Optional[str] = Field(None, description="Unique identifier of the notification as a string")
    user_id: Optional[str] = Field(None, description="ID of the user receiving the notification as a string")
    vendor_id: Optional[str] = Field(None, description="ID of the vendor receiving the notification as a string")
    type: str = Field(..., description="Type of notification (order/story/system)")
    message: str = Field(..., description="Message content of the notification")
    status: str = Field("unread", description="Status of the notification (unread/read)")
    related_id: Optional[str] = Field(None, description="ID of the related entity as a string")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @field_validator("id", "user_id", "vendor_id", "related_id", mode="before")
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @field_validator("user_id", "vendor_id")
    def ensure_at_least_one_recipient(cls, value, values):
        """Ensure at least one of user_id or vendor_id is provided."""
        if "user_id" in values and "vendor_id" in values:
            if values["user_id"] is None and value is None:
                raise ValueError("At least one of user_id or vendor_id must be provided")
        return value

    @field_validator("type")
    def validate_type(cls, value):
        """Ensure type is valid."""
        valid_types = ["order", "story", "system"]
        if value not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}, got: {value}")
        return value

    @field_validator("message")
    def validate_message(cls, value):
        """Ensure message is a non-empty string."""
        if not value or not isinstance(value, str):
            raise ValueError("Message must be a non-empty string")
        return value.strip()

    @field_validator("status")
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ["unread", "read"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

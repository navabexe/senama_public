# domain/entities/advertisement.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class Advertisement(BaseModel):
    """Entity representing an advertisement in the marketplace."""
    id: Optional[str] = Field(None, description="Unique identifier of the advertisement as a string")
    vendor_id: str = Field(..., description="ID of the vendor creating the advertisement as a string")
    type: str = Field(..., description="Type of advertisement ('story' or 'product')")
    related_id: str = Field(..., description="ID of the related story or product as a string")
    cost: float = Field(..., gt=0, description="Cost of the advertisement in IRR, must be positive")
    status: str = Field("pending", description="Status of the advertisement (pending/active/expired/rejected)")
    description: Optional[str] = Field(None, description="Optional description of the advertisement")
    starts_at: datetime = Field(..., description="Start time of the advertisement (UTC)")
    ends_at: datetime = Field(..., description="End time of the advertisement (UTC)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @field_validator("id", "vendor_id", "related_id", mode="before")
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @field_validator("type")
    def validate_type(cls, value):
        """Ensure type is either 'story' or 'product'."""
        valid_types = ["story", "product"]
        if value not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}, got: {value}")
        return value

    @field_validator("status")
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ["pending", "active", "expired", "rejected"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    @field_validator("starts_at", "ends_at", mode="before")
    def ensure_datetime_with_timezone(cls, value):
        """Ensure datetime fields have timezone information."""
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    raise ValueError("Datetime must include timezone information")
                return dt
            except ValueError as e:
                raise ValueError(f"Invalid datetime format: {str(e)}")
        if not value.tzinfo:
            raise ValueError("Datetime must include timezone information")
        return value

    @field_validator("ends_at")
    def ensure_ends_after_starts(cls, value, values):
        """Ensure ends_at is after starts_at."""
        if "starts_at" in values and value <= values["starts_at"]:
            raise ValueError("ends_at must be after starts_at")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

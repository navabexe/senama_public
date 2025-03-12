# domain/entities/report.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class Report(BaseModel):
    """Entity representing a report submitted by a user or vendor."""
    id: Optional[str] = Field(None, description="Unique identifier of the report as a string")
    reporter_id: str = Field(..., description="ID of the user or vendor submitting the report as a string")
    reported_id: str = Field(..., description="ID of the user, vendor, or entity being reported as a string")
    type: str = Field(..., description="Type of report (user/vendor/product/content)")
    reason: str = Field(..., description="Reason for the report")
    status: str = Field("pending", description="Status of the report (pending/reviewed/resolved)")
    details: Optional[str] = Field(None, description="Additional details about the report")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @field_validator("id", "reporter_id", "reported_id", mode="before")
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @field_validator("reporter_id")
    def prevent_cls_report(cls, value, values):
        """Ensure reporter_id is not the same as reported_id."""
        if "reported_id" in values and value == values["reported_id"]:
            raise ValueError("reporter_id cannot be the same as reported_id")
        return value

    @field_validator("type")
    def validate_type(cls, value):
        """Ensure type is valid."""
        valid_types = ["user", "vendor", "product", "content"]
        if value not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}, got: {value}")
        return value

    @field_validator("reason")
    def validate_reason(cls, value):
        """Ensure reason is a non-empty string."""
        if not value or not isinstance(value, str):
            raise ValueError("Reason must be a non-empty string")
        return value.strip()

    @field_validator("status")
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ["pending", "reviewed", "resolved"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    @field_validator("details")
    def validate_details(cls, value):
        """Ensure details is a valid string if provided."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Details must be a non-empty string if provided")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

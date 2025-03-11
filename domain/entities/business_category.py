# domain/entities/business_category.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, validator


class BusinessCategory(BaseModel):
    """Entity representing a business category in the marketplace."""
    id: Optional[str] = Field(None, description="Unique identifier of the business category as a string")
    name: str = Field(..., description="Name of the business category")
    description: Optional[str] = Field(None, description="Optional description of the business category")
    status: str = Field("active", description="Status of the business category (active/inactive)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @validator("id", pre=True)
    def validate_id_format(cls, value):
        """Validate that the ID field is a valid string."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @validator("name")
    def validate_name(cls, value):
        """Ensure the name is a non-empty string."""
        if not value or not isinstance(value, str):
            raise ValueError("Name must be a non-empty string")
        return value.strip()

    @validator("status")
    def validate_status(cls, value):
        """Ensure status is either 'active' or 'inactive'."""
        valid_statuses = ["active", "inactive"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

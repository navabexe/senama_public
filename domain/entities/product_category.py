# domain/entities/product_category.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, validator


class ProductCategory(BaseModel):
    """Entity representing a product category in the marketplace."""
    id: Optional[str] = Field(None, description="Unique identifier of the product category as a string")
    name: str = Field(..., description="Name of the product category")
    description: Optional[str] = Field(None, description="Optional description of the product category")
    status: str = Field("active", description="Status of the product category (active/inactive)")
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
        """Ensure name is a non-empty string."""
        if not value or not isinstance(value, str):
            raise ValueError("Name must be a non-empty string")
        return value.strip()

    @validator("description")
    def validate_description(cls, value):
        """Ensure description is a valid string if provided."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value

    @validator("status")
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ["active", "inactive"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

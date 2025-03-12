# domain/entities/product.py
from datetime import datetime, timezone
from typing import Optional, List, Dict

from pydantic import BaseModel, Field,  field_validator


class Product(BaseModel):
    """Entity representing a product in the marketplace."""
    id: Optional[str] = Field(None, description="Unique identifier of the product as a string")
    vendor_id: str = Field(..., description="ID of the vendor owning the product as a string")
    name: str = Field(..., description="Name of the product")
    description: Optional[str] = Field(None, description="Description of the product")
    price: float = Field(..., gt=0, description="Price of the product in IRR, must be positive")
    currency: str = Field("IRR", description="Currency of the price (default: IRR)")
    stock: int = Field(..., ge=0, description="Available stock quantity, must be non-negative")
    images: Optional[List[str]] = Field(None, description="List of image URLs")
    videos: Optional[List[str]] = Field(None, description="List of video URLs")
    technical_specs: Optional[Dict[str, str]] = Field(None, description="Technical specifications as key-value pairs")
    category_ids: Optional[List[str]] = Field(None, description="List of category IDs as strings")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    status: str = Field("active", description="Status of the product (active/inactive)")
    linked_vendors: Optional[List[str]] = Field(None, description="List of linked vendor IDs as strings")
    suggested_products: Optional[List[str]] = Field(None, description="List of suggested product IDs as strings")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @field_validator("id", "vendor_id", "category_ids", "linked_vendors", "suggested_products", mode="before")
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is None:
            return value
        if isinstance(value, list):
            if not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError(f"All IDs in list must be non-empty strings, got: {value}")
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @field_validator("name")
    def validate_name(cls, value):
        """Ensure name is a non-empty string."""
        if not value or not isinstance(value, str):
            raise ValueError("Name must be a non-empty string")
        return value.strip()

    @field_validator("description", "currency")
    def validate_optional_strings(cls, value):
        """Ensure optional string fields are valid if provided."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Field must be a non-empty string if provided")
        return value

    @field_validator("images", "videos", "tags")
    def validate_string_lists(cls, value):
        """Ensure list fields contain valid strings if provided."""
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Field must be a list of non-empty strings if provided")
        return value

    @field_validator("technical_specs")
    def validate_technical_specs(cls, value):
        """Ensure technical_specs is a dictionary of strings if provided."""
        if value is not None:
            if not isinstance(value, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in value.items()
            ):
                raise ValueError("technical_specs must be a dictionary with string keys and values if provided")
        return value

    @field_validator("status")
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

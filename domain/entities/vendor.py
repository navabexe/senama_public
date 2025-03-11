# domain/entities/vendor.py
from datetime import datetime, timezone
from typing import Optional, List

from pydantic import BaseModel, Field, validator


class Vendor(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier of the vendor as a string")
    phone: str = Field(..., description="Phone number of the vendor")
    business_name: str = Field(..., description="Name of the vendor's business")
    description: Optional[str] = Field(None, description="Description of the vendor's business")
    category_ids: Optional[List[str]] = Field(None, description="List of business category IDs as strings")
    roles: List[str] = Field(default_factory=lambda: ["vendor"], description="Roles assigned to the vendor")
    status: str = Field("active", description="Status of the vendor (active/inactive)")
    avatar_urls: Optional[List[str]] = Field(None, description="List of avatar image URLs")
    wallet_balance: float = Field(0.0, ge=0, description="Current wallet balance in IRR, must be non-negative")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @validator("id", "category_ids", pre=True)
    def validate_id_format(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            if not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError(f"All IDs in list must be non-empty strings, got: {value}")
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @validator("phone")
    def validate_phone(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Phone must be a non-empty string")
        return value.strip()

    @validator("business_name")
    def validate_business_name(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Business name must be a non-empty string")
        return value.strip()

    @validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value

    @validator("roles")
    def validate_roles(cls, value):
        if not value or not isinstance(value, list) or not all(isinstance(r, str) and r.strip() for r in value):
            raise ValueError("Roles must be a non-empty list of strings")
        return value

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "inactive"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    @validator("avatar_urls")
    def validate_avatar_urls(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(url, str) and url.strip() for url in value):
                raise ValueError("Avatar URLs must be a list of non-empty strings if provided")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

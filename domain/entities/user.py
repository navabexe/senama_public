# domain/entities/user.py
from datetime import datetime, timezone
from typing import Optional, List

from pydantic import BaseModel, Field,  field_validator


class User(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier of the user as a string")
    phone: str = Field(..., description="Phone number of the user")
    first_name: Optional[str] = Field(None, description="First name of the user")
    last_name: Optional[str] = Field(None, description="Last name of the user")
    roles: List[str] = Field(default_factory=lambda: ["user"], description="Roles assigned to the user")
    status: str = Field("active", description="Status of the user (active/inactive)")
    avatar_urls: Optional[List[str]] = Field(None, description="List of avatar image URLs")
    following_vendor_ids: Optional[List[str]] = Field(None, description="List of vendor IDs the user follows")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @field_validator("id", "following_vendor_ids", mode="before")
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

    @field_validator("phone")
    def validate_phone(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Phone must be a non-empty string")
        return value.strip()

    @field_validator("first_name", "last_name")
    def validate_names(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Name must be a non-empty string if provided")
        return value

    @field_validator("roles")
    def validate_roles(cls, value):
        if not value or not isinstance(value, list) or not all(isinstance(r, str) and r.strip() for r in value):
            raise ValueError("Roles must be a non-empty list of strings")
        return value

    @field_validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "inactive"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    @field_validator("avatar_urls")
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

# domain/schemas/user.py
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator


class UserCreate(BaseModel):
    phone: str = Field(..., description="Phone number of the user")
    first_name: Optional[str] = Field(None, description="First name of the user")
    last_name: Optional[str] = Field(None, description="Last name of the user")

    @validator("phone")
    def validate_phone(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Phone must be a non-empty string")
        return value.strip()

    @validator("first_name", "last_name")
    def validate_names(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Name must be a non-empty string if provided")
        return value


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, description="Updated first name")
    last_name: Optional[str] = Field(None, description="Updated last name")
    status: Optional[str] = Field(None, description="Updated status of the user")
    avatar_urls: Optional[List[str]] = Field(None, description="Updated list of avatar URLs")
    following_vendor_ids: Optional[List[str]] = Field(None, description="Updated list of followed vendor IDs")

    @validator("first_name", "last_name")
    def validate_names(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Name must be a non-empty string if provided")
        return value

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "inactive"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

    @validator("avatar_urls", "following_vendor_ids")
    def validate_lists(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Field must be a list of non-empty strings if provided")
        return value


class UserResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the user as a string")
    phone: str = Field(..., description="Phone number of the user")
    first_name: Optional[str] = Field(None, description="First name of the user")
    last_name: Optional[str] = Field(None, description="Last name of the user")
    roles: List[str] = Field(..., description="Roles assigned to the user")
    status: str = Field(..., description="Status of the user")
    avatar_urls: Optional[List[str]] = Field(None, description="List of avatar URLs")
    following_vendor_ids: Optional[List[str]] = Field(None, description="List of followed vendor IDs")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

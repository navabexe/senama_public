# domain/schemas/business_category.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class BusinessCategoryCreate(BaseModel):
    name: str = Field(..., description="Name of the business category")
    description: Optional[str] = Field(None, description="Optional description of the business category")

    @field_validator("name")
    def validate_name(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Name must be a non-empty string")
        return value.strip()

    @field_validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value


class BusinessCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated name of the business category")
    description: Optional[str] = Field(None, description="Updated description of the business category")
    status: Optional[str] = Field(None, description="Updated status of the business category")

    @field_validator("name")
    def validate_name(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Name must be a non-empty string if provided")
        return value

    @field_validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value

    @field_validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "inactive"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value


class BusinessCategoryResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the business category as a string")
    name: str = Field(..., description="Name of the business category")
    description: Optional[str] = Field(None, description="Description of the business category")
    status: str = Field(..., description="Status of the business category")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

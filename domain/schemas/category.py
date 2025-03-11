# domain/schemas/category.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class CategoryCreate(BaseModel):
    name: str = Field(..., description="Name of the category")
    description: Optional[str] = Field(None, description="Optional description of the category")

    @validator("name")
    def validate_name(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Name must be a non-empty string")
        return value.strip()

    @validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated name of the category")
    description: Optional[str] = Field(None, description="Updated description of the category")
    status: Optional[str] = Field(None, description="Updated status of the category")

    @validator("name")
    def validate_name(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Name must be a non-empty string if provided")
        return value

    @validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "inactive"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value


class CategoryResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the category as a string")
    name: str = Field(..., description="Name of the category")
    description: Optional[str] = Field(None, description="Description of the category")
    status: str = Field(..., description="Status of the category")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

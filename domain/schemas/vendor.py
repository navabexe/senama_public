# domain/schemas/vendor.py
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator


class VendorCreate(BaseModel):
    phone: str = Field(..., description="Phone number of the vendor")
    business_name: str = Field(..., description="Name of the vendor's business")
    description: Optional[str] = Field(None, description="Description of the vendor's business")
    category_ids: Optional[List[str]] = Field(None, description="List of business category IDs")

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

    @validator("category_ids")
    def validate_category_ids(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Category IDs must be a list of non-empty strings if provided")
        return value


class VendorUpdate(BaseModel):
    phone: Optional[str] = Field(None, description="Updated phone number")
    business_name: Optional[str] = Field(None, description="Updated business name")
    description: Optional[str] = Field(None, description="Updated description")
    category_ids: Optional[List[str]] = Field(None, description="Updated list of category IDs")
    status: Optional[str] = Field(None, description="Updated status of the vendor")
    avatar_urls: Optional[List[str]] = Field(None, description="Updated list of avatar URLs")
    wallet_balance: Optional[float] = Field(None, ge=0, description="Updated wallet balance in IRR")

    @validator("phone")
    def validate_phone(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Phone must be a non-empty string if provided")
        return value

    @validator("business_name")
    def validate_business_name(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Business name must be a non-empty string if provided")
        return value

    @validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value

    @validator("category_ids")
    def validate_category_ids(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Category IDs must be a list of non-empty strings if provided")
        return value

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "inactive"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

    @validator("avatar_urls")
    def validate_avatar_urls(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Avatar URLs must be a list of non-empty strings if provided")
        return value


class VendorResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the vendor as a string")
    phone: str = Field(..., description="Phone number of the vendor")
    business_name: str = Field(..., description="Name of the vendor's business")
    description: Optional[str] = Field(None, description="Description of the vendor's business")
    category_ids: Optional[List[str]] = Field(None, description="List of business category IDs")
    roles: List[str] = Field(..., description="Roles assigned to the vendor")
    status: str = Field(..., description="Status of the vendor")
    avatar_urls: Optional[List[str]] = Field(None, description="List of avatar URLs")
    wallet_balance: float = Field(..., description="Current wallet balance in IRR")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

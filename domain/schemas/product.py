# domain/schemas/product.py
from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, Field,  field_validator


class ProductCreate(BaseModel):
    name: str = Field(..., description="Name of the product")
    description: Optional[str] = Field(None, description="Description of the product")
    price: float = Field(..., gt=0, description="Price of the product in IRR, must be positive")
    currency: str = Field("IRR", description="Currency of the price")
    stock: int = Field(..., ge=0, description="Available stock quantity, must be non-negative")
    images: Optional[List[str]] = Field(None, description="List of image URLs")
    videos: Optional[List[str]] = Field(None, description="List of video URLs")
    technical_specs: Optional[Dict[str, str]] = Field(None, description="Technical specifications")
    category_ids: Optional[List[str]] = Field(None, description="List of category IDs as strings")
    tags: Optional[List[str]] = Field(None, description="List of tags")

    @field_validator("name")
    def validate_name(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Name must be a non-empty string")
        return value.strip()

    @field_validator("description", "currency")
    def validate_optional_strings(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Field must be a non-empty string if provided")
        return value

    @field_validator("category_ids", mode="before")
    def validate_category_ids(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Category IDs must be a list of non-empty strings")
        return value

    @field_validator("images", "videos", "tags")
    def validate_string_lists(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Field must be a list of non-empty strings if provided")
        return value

    @field_validator("technical_specs")
    def validate_technical_specs(cls, value):
        if value is not None:
            if not isinstance(value, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
                raise ValueError("Technical specs must be a dictionary with string keys and values")
        return value


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated name of the product")
    description: Optional[str] = Field(None, description="Updated description")
    price: Optional[float] = Field(None, gt=0, description="Updated price in IRR, must be positive")
    currency: Optional[str] = Field(None, description="Updated currency")
    stock: Optional[int] = Field(None, ge=0, description="Updated stock quantity, must be non-negative")
    images: Optional[List[str]] = Field(None, description="Updated list of image URLs")
    videos: Optional[List[str]] = Field(None, description="Updated list of video URLs")
    technical_specs: Optional[Dict[str, str]] = Field(None, description="Updated technical specifications")
    category_ids: Optional[List[str]] = Field(None, description="Updated list of category IDs")
    tags: Optional[List[str]] = Field(None, description="Updated list of tags")
    status: Optional[str] = Field(None, description="Updated status of the product")

    @field_validator("name")
    def validate_name(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Name must be a non-empty string if provided")
        return value

    @field_validator("description", "currency")
    def validate_optional_strings(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Field must be a non-empty string if provided")
        return value

    @field_validator("category_ids", mode="before")
    def validate_category_ids(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Category IDs must be a list of non-empty strings")
        return value

    @field_validator("images", "videos", "tags")
    def validate_string_lists(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("Field must be a list of non-empty strings if provided")
        return value

    @field_validator("technical_specs")
    def validate_technical_specs(cls, value):
        if value is not None:
            if not isinstance(value, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
                raise ValueError("Technical specs must be a dictionary with string keys and values")
        return value

    @field_validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "inactive"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value


class ProductResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the product as a string")
    vendor_id: str = Field(..., description="ID of the vendor as a string")
    name: str = Field(..., description="Name of the product")
    description: Optional[str] = Field(None, description="Description of the product")
    price: float = Field(..., description="Price of the product in IRR")
    currency: str = Field(..., description="Currency of the price")
    stock: int = Field(..., description="Available stock quantity")
    images: Optional[List[str]] = Field(None, description="List of image URLs")
    videos: Optional[List[str]] = Field(None, description="List of video URLs")
    technical_specs: Optional[Dict[str, str]] = Field(None, description="Technical specifications")
    category_ids: Optional[List[str]] = Field(None, description="List of category IDs")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    status: str = Field(..., description="Status of the product")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

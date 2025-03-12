# domain/schemas/vendor.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime

class VendorCreate(BaseModel):
    username: str = Field(..., description="Unique username of the vendor")
    name: str = Field(..., description="Name of the vendor (business name)")
    owner_name: str = Field(..., description="Name of the vendor's owner")
    phone: str = Field(..., description="Phone number of the vendor")
    business_category_ids: List[str] = Field(..., description="List of business category IDs")
    address: str = Field(..., description="Street address of the vendor")
    city: str = Field(..., description="City of the vendor")
    province: str = Field(..., description="Province or state of the vendor")
    location: Dict[str, float] = Field(..., description="Geographical coordinates (lat, lng)")
    description: Optional[str] = Field(None, description="Description of the vendor's business")
    status: Optional[str] = Field("pending", description="Status of the vendor")
    avatar_urls: Optional[List[str]] = Field(default_factory=list, description="List of avatar URLs")
    wallet_balance: Optional[float] = Field(0.0, ge=0, description="Wallet balance in IRR")
    products: Optional[List[str]] = Field(default_factory=list, description="List of product IDs")
    stories: Optional[List[str]] = Field(default_factory=list, description="List of story IDs")
    roles: Optional[List[str]] = Field(default_factory=lambda: ["vendor"], description="Roles assigned to the vendor")

    @field_validator("phone")
    def validate_phone(cls, value):
        if not value or not value.startswith("+"):
            raise ValueError("Phone number must start with '+'")
        return value.strip()

    @field_validator("username")
    def validate_username(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Username must be a non-empty string")
        return value.strip()

    @field_validator("name")
    def validate_name(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Name must be a non-empty string")
        return value.strip()

    @field_validator("owner_name")
    def validate_owner_name(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Owner name must be a non-empty string")
        return value.strip()

    @field_validator("business_category_ids")
    def validate_category_ids(cls, value):
        if not value or not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
            raise ValueError("Business category IDs must be a non-empty list of non-empty strings")
        return value

    @field_validator("address")
    def validate_address(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Address must be a non-empty string")
        return value.strip()

    @field_validator("city")
    def validate_city(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("City must be a non-empty string")
        return value.strip()

    @field_validator("province")
    def validate_province(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Province must be a non-empty string")
        return value.strip()

    @field_validator("location")
    def validate_location(cls, value):
        if not isinstance(value, dict) or "lat" not in value or "lng" not in value:
            raise ValueError("Location must be a dict containing 'lat' and 'lng'")
        return value

    @field_validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value

class VendorUpdate(BaseModel):
    username: Optional[str] = Field(None, description="Updated username")
    name: Optional[str] = Field(None, description="Updated business name")
    owner_name: Optional[str] = Field(None, description="Updated owner name")
    phone: Optional[str] = Field(None, description="Updated phone number")
    business_category_ids: Optional[List[str]] = Field(None, description="Updated list of category IDs")
    address: Optional[str] = Field(None, description="Updated address")
    city: Optional[str] = Field(None, description="Updated city")
    province: Optional[str] = Field(None, description="Updated province")
    location: Optional[Dict[str, float]] = Field(None, description="Updated geographical coordinates")
    description: Optional[str] = Field(None, description="Updated description")
    status: Optional[str] = Field(None, description="Updated status")
    avatar_urls: Optional[List[str]] = Field(None, description="Updated list of avatar URLs")
    wallet_balance: Optional[float] = Field(None, ge=0, description="Updated wallet balance in IRR")
    products: Optional[List[str]] = Field(None, description="Updated list of product IDs")
    stories: Optional[List[str]] = Field(None, description="Updated list of story IDs")

    @field_validator("username")
    def validate_username(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Username must be a non-empty string if provided")
        return value

    @field_validator("name")
    def validate_name(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Name must be a non-empty string if provided")
        return value

    @field_validator("owner_name")
    def validate_owner_name(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Owner name must be a non-empty string if provided")
        return value

    @field_validator("phone")
    def validate_phone(cls, value):
        if value is not None and (not value.startswith("+") or not value.strip()):
            raise ValueError("Phone number must start with '+' and be non-empty if provided")
        return value

    @field_validator("business_category_ids")
    def validate_category_ids(cls, value):
        if value is not None and (not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value)):
            raise ValueError("Business category IDs must be a list of non-empty strings if provided")
        return value

    @field_validator("address")
    def validate_address(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Address must be a non-empty string if provided")
        return value

    @field_validator("city")
    def validate_city(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("City must be a non-empty string if provided")
        return value

    @field_validator("province")
    def validate_province(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Province must be a non-empty string if provided")
        return value

    @field_validator("location")
    def validate_location(cls, value):
        if value is not None and (not isinstance(value, dict) or "lat" not in value or "lng" not in value):
            raise ValueError("Location must be a dict containing 'lat' and 'lng' if provided")
        return value

    @field_validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value

    @field_validator("status")
    def validate_status(cls, value):
        valid_statuses = ["pending", "active", "inactive"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

class VendorResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the vendor as a string")
    username: str = Field(..., description="Unique username of the vendor")
    name: str = Field(..., description="Name of the vendor (business name)")
    owner_name: str = Field(..., description="Name of the vendor's owner")
    phone: str = Field(..., description="Phone number of the vendor")
    business_category_ids: List[str] = Field(..., description="List of business category IDs")
    address: str = Field(..., description="Street address of the vendor")
    city: str = Field(..., description="City of the vendor")
    province: str = Field(..., description="Province or state of the vendor")
    location: Dict[str, float] = Field(..., description="Geographical coordinates (lat, lng)")
    description: Optional[str] = Field(None, description="Description of the vendor's business")
    status: str = Field(..., description="Status of the vendor")
    avatar_urls: List[str] = Field(..., description="List of avatar URLs")
    wallet_balance: float = Field(..., ge=0, description="Wallet balance in IRR")
    products: List[str] = Field(..., description="List of product IDs")
    stories: List[str] = Field(..., description="List of story IDs")
    roles: List[str] = Field(..., description="Roles assigned to the vendor")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
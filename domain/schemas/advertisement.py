# domain/schemas/advertisement.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class AdvertisementCreate(BaseModel):
    type: str = Field(..., description="Type of advertisement ('story' or 'product')")
    related_id: str = Field(..., description="ID of the related story or product as a string")
    cost: float = Field(..., gt=0, description="Cost of the advertisement in IRR")
    description: Optional[str] = Field(None, description="Optional description of the advertisement")
    starts_at: datetime = Field(..., description="Start time of the advertisement (UTC)")
    ends_at: datetime = Field(..., description="End time of the advertisement (UTC)")

    @field_validator("type")
    def validate_type(cls, value):
        if value not in ["story", "product"]:
            raise ValueError("Type must be 'story' or 'product'")
        return value

    @field_validator("related_id", mode="before")
    def validate_related_id(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Related ID must be a non-empty string")
        return value

    @field_validator("starts_at", "ends_at", mode="before")
    def ensure_datetime_with_timezone(cls, value):
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                raise ValueError("Datetime must include timezone information")
            return dt
        if not value.tzinfo:
            raise ValueError("Datetime must include timezone information")
        return value

    @field_validator("ends_at")
    def ensure_ends_after_starts(cls, value, values):
        if "starts_at" in values and value <= values["starts_at"]:
            raise ValueError("ends_at must be after starts_at")
        return value


class AdvertisementUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Status of the advertisement")
    description: Optional[str] = Field(None, description="Updated description")
    starts_at: Optional[datetime] = Field(None, description="Updated start time (UTC)")
    ends_at: Optional[datetime] = Field(None, description="Updated end time (UTC)")

    @field_validator("status")
    def validate_status(cls, value):
        valid_statuses = ["pending", "active", "expired", "rejected"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

    @field_validator("starts_at", "ends_at", mode="before")
    def ensure_datetime_with_timezone(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                raise ValueError("Datetime must include timezone information")
            return dt
        if not value.tzinfo:
            raise ValueError("Datetime must include timezone information")
        return value

    @field_validator("ends_at")
    def ensure_ends_after_starts(cls, value, values):
        if value is not None and "starts_at" in values and values["starts_at"] is not None:
            if value <= values["starts_at"]:
                raise ValueError("ends_at must be after starts_at")
        return value


class AdvertisementResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the advertisement as a string")
    vendor_id: str = Field(..., description="ID of the vendor owning the advertisement as a string")
    type: str = Field(..., description="Type of advertisement ('story' or 'product')")
    related_id: str = Field(..., description="ID of the related story or product as a string")
    cost: float = Field(..., description="Cost of the advertisement in IRR")
    status: str = Field(..., description="Current status of the advertisement")
    description: Optional[str] = Field(None, description="Description of the advertisement")
    starts_at: datetime = Field(..., description="Start time of the advertisement (UTC)")
    ends_at: datetime = Field(..., description="End time of the advertisement (UTC)")
    created_at: datetime = Field(..., description="Creation time of the advertisement (UTC)")
    updated_at: datetime = Field(..., description="Last update time of the advertisement (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

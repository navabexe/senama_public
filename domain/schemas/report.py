# domain/schemas/report.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class ReportCreate(BaseModel):
    reported_id: str = Field(..., description="ID of the entity being reported as a string")
    type: str = Field(..., description="Type of report (user/vendor/product/content)")
    reason: str = Field(..., description="Reason for the report")
    details: Optional[str] = Field(None, description="Additional details about the report")

    @field_validator("reported_id", mode="before")
    def validate_reported_id(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Reported ID must be a non-empty string")
        return value

    @field_validator("type")
    def validate_type(cls, value):
        valid_types = ["user", "vendor", "product", "content"]
        if value not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}")
        return value

    @field_validator("reason")
    def validate_reason(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Reason must be a non-empty string")
        return value.strip()

    @field_validator("details")
    def validate_details(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Details must be a non-empty string if provided")
        return value


class ReportUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated status of the report")

    @field_validator("status")
    def validate_status(cls, value):
        valid_statuses = ["pending", "reviewed", "resolved"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value


class ReportResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the report as a string")
    reporter_id: str = Field(..., description="ID of the reporter as a string")
    reported_id: str = Field(..., description="ID of the entity being reported as a string")
    type: str = Field(..., description="Type of report")
    reason: str = Field(..., description="Reason for the report")
    status: str = Field(..., description="Status of the report")
    details: Optional[str] = Field(None, description="Additional details about the report")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# domain/schemas/session.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class SessionCreate(BaseModel):
    user_id: str = Field(..., description="ID of the user or vendor as a string")
    access_token: str = Field(..., description="Access token for the session")
    refresh_token: Optional[str] = Field(None, description="Refresh token for the session")
    device_info: Optional[str] = Field(None, description="Device information for the session")
    expires_at: datetime = Field(..., description="Expiration time of the session (UTC)")

    @validator("user_id", pre=True)
    def validate_user_id(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("User ID must be a non-empty string")
        return value

    @validator("access_token", "refresh_token")
    def validate_tokens(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Token must be a non-empty string if provided")
        return value

    @validator("device_info")
    def validate_device_info(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Device info must be a non-empty string if provided")
        return value

    @validator("expires_at", pre=True)
    def validate_expires_at(cls, value):
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                raise ValueError("Expires_at must include timezone information")
            return dt
        if not value.tzinfo:
            raise ValueError("Expires_at must include timezone information")
        return value


class SessionUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated status of the session")

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "revoked"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value


class SessionResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the session as a string")
    user_id: str = Field(..., description="ID of the user or vendor as a string")
    access_token: str = Field(..., description="Access token for the session")
    refresh_token: Optional[str] = Field(None, description="Refresh token for the session")
    status: str = Field(..., description="Status of the session")
    device_info: Optional[str] = Field(None, description="Device information for the session")
    expires_at: datetime = Field(..., description="Expiration time of the session (UTC)")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

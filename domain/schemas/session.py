from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SessionCreate(BaseModel):
    """Schema for creating a new session after user authentication."""

    user_id: str = Field(..., description="ID of the authenticated user or vendor")
    access_token: str = Field(..., description="JWT access token for authentication")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token for renewing access")
    device_info: Optional[str] = Field(None, description="Device details (if available)")
    expires_at: datetime = Field(..., description="Expiration timestamp for the access token (UTC)")

    @field_validator("user_id", mode="before")
    def validate_user_id(cls, value):
        """Ensure user_id is a valid, non-empty string."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("User ID must be a non-empty string")
        return value

    @field_validator("access_token", "refresh_token")
    def validate_tokens(cls, value):
        """Ensure tokens are valid, non-empty strings if provided."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Token must be a non-empty string if provided")
        return value

    @field_validator("device_info")
    def validate_device_info(cls, value):
        """Ensure device_info is a valid, non-empty string if provided."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Device info must be a non-empty string if provided")
        return value

    @field_validator("expires_at", mode="before")
    def validate_expires_at(cls, value):
        """Ensure expires_at has timezone information."""
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                raise ValueError("Expires_at must include timezone information")
            return dt
        if not value.tzinfo:
            raise ValueError("Expires_at must include timezone information")
        return value


class SessionUpdate(BaseModel):
    """Schema for updating an existing session status (e.g., revoking a session)."""

    status: Optional[str] = Field(None, description="Updated status of the session")

    @field_validator("status")
    def validate_status(cls, value):
        """Ensure status is either 'active' or 'revoked'."""
        valid_statuses = ["active", "revoked"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value


class SessionResponse(BaseModel):
    """Schema for returning session details after authentication or token refresh."""

    id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="ID of the authenticated user or vendor")
    access_token: str = Field(..., description="JWT access token for authentication")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token for renewing access")
    status: str = Field(..., description="Current session status ('active' or 'revoked')")
    device_info: Optional[str] = Field(None, description="Device details (if available)")
    expires_at: datetime = Field(..., description="Expiration timestamp for the access token (UTC)")
    created_at: datetime = Field(..., description="Timestamp when the session was created (UTC)")
    updated_at: datetime = Field(..., description="Timestamp of the last session update (UTC)")

    class Config:
        """Custom JSON serialization for datetime fields."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

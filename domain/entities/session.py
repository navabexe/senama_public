# domain/entities/session.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, validator


class Session(BaseModel):
    """Entity representing a user or vendor session in the marketplace."""
    id: Optional[str] = Field(None, description="Unique identifier of the session as a string")
    user_id: str = Field(..., description="ID of the user or vendor associated with the session as a string")
    access_token: str = Field(..., description="Access token for the session")
    refresh_token: Optional[str] = Field(None, description="Refresh token for the session")
    status: str = Field("active", description="Status of the session (active/revoked)")
    device_info: Optional[str] = Field(None, description="Information about the device used for the session")
    expires_at: datetime = Field(..., description="Expiration time of the session (UTC)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @validator("id", "user_id", pre=True)
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @validator("access_token", "refresh_token")
    def validate_token_format(cls, value):
        """Ensure token fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Token must be a non-empty string if provided")
        return value

    @validator("status")
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ["active", "revoked"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    @validator("device_info")
    def validate_device_info(cls, value):
        """Ensure device_info is a valid string if provided."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Device info must be a non-empty string if provided")
        return value

    @validator("expires_at", pre=True)
    def ensure_datetime_with_timezone(cls, value):
        """Ensure expires_at has timezone information."""
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    raise ValueError("Expires_at must include timezone information")
                return dt
            except ValueError as e:
                raise ValueError(f"Invalid datetime format for expires_at: {str(e)}")
        if not value.tzinfo:
            raise ValueError("Expires_at must include timezone information")
        return value

    @validator("expires_at")
    def ensure_future_expiration(cls, value):
        """Ensure expires_at is in the future relative to created_at."""
        now = datetime.now(timezone.utc)
        if value <= now:
            raise ValueError("expires_at must be a future date")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

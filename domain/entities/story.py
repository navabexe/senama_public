# domain/entities/story.py
from datetime import datetime, timezone
from typing import Optional, List

from pydantic import BaseModel, Field,  field_validator


class Story(BaseModel):
    """Entity representing a story in the marketplace."""
    id: Optional[str] = Field(None, description="Unique identifier of the story 1story as a string")
    vendor_id: str = Field(..., description="ID of the vendor posting the story as a string")
    content: str = Field(..., description="Content of the story (text or media URL)")
    media_type: str = Field(..., description="Type of media (image/video/text)")
    status: str = Field("active", description="Status of the story (active/expired)")
    views: int = Field(0, ge=0, description="Number of views, must be non-negative")
    tags: Optional[List[str]] = Field(None, description="List of tags associated with the story")
    expires_at: datetime = Field(..., description="Expiration time of the story (UTC)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @field_validator("id", "vendor_id", mode="before")
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @field_validator("content")
    def validate_content(cls, value):
        """Ensure content is a non-empty string."""
        if not value or not isinstance(value, str):
            raise ValueError("Content must be a non-empty string")
        return value.strip()

    @field_validator("media_type")
    def validate_media_type(cls, value):
        """Ensure media_type is valid."""
        valid_types = ["image", "video", "text"]
        if value not in valid_types:
            raise ValueError(f"Media type must be one of {valid_types}, got: {value}")
        return value

    @field_validator("status")
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ["active", "expired"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    @field_validator("tags")
    def validate_tags(cls, value):
        """Ensure tags is a list of valid strings if provided."""
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(t, str) and t.strip() for t in value):
                raise ValueError("Tags must be a list of non-empty strings if provided")
        return value

    @field_validator("expires_at", mode="before")
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

    @field_validator("expires_at")
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

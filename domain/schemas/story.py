# domain/schemas/story.py
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator


class StoryCreate(BaseModel):
    content: str = Field(..., description="Content of the story (text or media URL)")
    media_type: str = Field(..., description="Type of media (image/video/text)")
    tags: Optional[List[str]] = Field(None, description="List of tags for the story")
    expires_at: datetime = Field(..., description="Expiration time of the story (UTC)")

    @validator("content")
    def validate_content(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("Content must be a non-empty string")
        return value.strip()

    @validator("media_type")
    def validate_media_type(cls, value):
        valid_types = ["image", "video", "text"]
        if value not in valid_types:
            raise ValueError(f"Media type must be one of {valid_types}")
        return value

    @validator("tags")
    def validate_tags(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(t, str) and t.strip() for t in value):
                raise ValueError("Tags must be a list of non-empty strings if provided")
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


class StoryUpdate(BaseModel):
    content: Optional[str] = Field(None, description="Updated content of the story")
    media_type: Optional[str] = Field(None, description="Updated media type")
    tags: Optional[List[str]] = Field(None, description="Updated list of tags")
    status: Optional[str] = Field(None, description="Updated status of the story")
    expires_at: Optional[datetime] = Field(None, description="Updated expiration time (UTC)")

    @validator("content")
    def validate_content(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Content must be a non-empty string if provided")
        return value

    @validator("media_type")
    def validate_media_type(cls, value):
        valid_types = ["image", "video", "text"]
        if value is not None and value not in valid_types:
            raise ValueError(f"Media type must be one of {valid_types}")
        return value

    @validator("tags")
    def validate_tags(cls, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(t, str) and t.strip() for t in value):
                raise ValueError("Tags must be a list of non-empty strings if provided")
        return value

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["active", "expired"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

    @validator("expires_at", pre=True)
    def validate_expires_at(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                raise ValueError("Expires_at must include timezone information")
            return dt
        if not value.tzinfo:
            raise ValueError("Expires_at must include timezone information")
        return value


class StoryResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the story as a string")
    vendor_id: str = Field(..., description="ID of the vendor as a string")
    content: str = Field(..., description="Content of the story")
    media_type: str = Field(..., description="Type of media")
    status: str = Field(..., description="Status of the story")
    views: int = Field(..., description="Number of views")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    expires_at: datetime = Field(..., description="Expiration time (UTC)")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

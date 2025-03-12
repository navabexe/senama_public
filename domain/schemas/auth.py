from typing import Optional, List

from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    """Schema for user and vendor registration"""
    phone: str = Field(..., description="User phone number")
    role: str = Field(..., pattern="^(user|vendor)$", description="Role must be 'user' or 'vendor'")
    name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    business_category_ids: Optional[List[str]] = None

    @classmethod
    def validate_phone(cls, value):
        if not value.startswith("+") or len(value) < 10:
            raise ValueError("Invalid phone number format")
        return value.strip()
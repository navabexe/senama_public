# domain/entities/transaction.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, validator


class Transaction(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier of the transaction as a string")
    vendor_id: str = Field(..., description="ID of the vendor involved in the transaction as a string")
    amount: float = Field(..., description="Amount of the transaction in IRR")
    type: str = Field(..., description="Type of transaction (deposit/withdrawal)")
    status: str = Field("pending", description="Status of the transaction (pending/completed/failed)")
    description: Optional[str] = Field(None, description="Optional description of the transaction")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @validator("id", "vendor_id", pre=True)
    def validate_id_format(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @validator("amount")
    def validate_amount(cls, value):
        if value <= 0:
            raise ValueError("Amount must be positive")
        return value

    @validator("type")
    def validate_type(cls, value):
        valid_types = ["deposit", "withdrawal"]
        if value not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}, got: {value}")
        return value

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["pending", "completed", "failed"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    @validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

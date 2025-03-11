# domain/schemas/transaction.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class TransactionCreate(BaseModel):
    amount: float = Field(..., description="Amount of the transaction in IRR")
    type: str = Field(..., description="Type of transaction (deposit/withdrawal)")
    description: Optional[str] = Field(None, description="Optional description of the transaction")

    @validator("amount")
    def validate_amount(cls, value):
        if value <= 0:
            raise ValueError("Amount must be positive")
        return value

    @validator("type")
    def validate_type(cls, value):
        valid_types = ["deposit", "withdrawal"]
        if value not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}")
        return value

    @validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value


class TransactionUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated status of the transaction")
    description: Optional[str] = Field(None, description="Updated description of the transaction")

    @validator("status")
    def validate_status(cls, value):
        valid_statuses = ["pending", "completed", "failed"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

    @validator("description")
    def validate_description(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Description must be a non-empty string if provided")
        return value


class TransactionResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the transaction as a string")
    vendor_id: str = Field(..., description="ID of the vendor as a string")
    amount: float = Field(..., description="Amount of the transaction in IRR")
    type: str = Field(..., description="Type of transaction")
    status: str = Field(..., description="Status of the transaction")
    description: Optional[str] = Field(None, description="Description of the transaction")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

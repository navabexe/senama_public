# domain/schemas/order.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field,  field_validator


class OrderCreate(BaseModel):
    vendor_id: str = Field(..., description="ID of the vendor as a string")
    product_id: str = Field(..., description="ID of the product as a string")
    quantity: int = Field(..., ge=1, description="Quantity of the product, must be positive")
    shipping_address: Optional[str] = Field(None, description="Shipping address for the order")
    notes: Optional[str] = Field(None, description="Optional notes for the order")

    @field_validator("vendor_id", "product_id", mode="before")
    def validate_id_format(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ID must be a non-empty string")
        return value

    @field_validator("shipping_address", "notes")
    def validate_optional_strings(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Field must be a non-empty string if provided")
        return value


class OrderUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated status of the order")
    shipping_address: Optional[str] = Field(None, description="Updated shipping address")
    notes: Optional[str] = Field(None, description="Updated notes")
    payment_status: Optional[str] = Field(None, description="Updated payment status")

    @field_validator("status")
    def validate_status(cls, value):
        valid_statuses = ["pending", "accepted", "delivered", "cancelled"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

    @field_validator("shipping_address", "notes")
    def validate_optional_strings(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Field must be a non-empty string if provided")
        return value

    @field_validator("payment_status")
    def validate_payment_status(cls, value):
        valid_statuses = ["unpaid", "paid", "failed"]
        if value is not None and value not in valid_statuses:
            raise ValueError(f"Payment status must be one of {valid_statuses}")
        return value


class OrderResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the order as a string")
    user_id: str = Field(..., description="ID of the user as a string")
    vendor_id: str = Field(..., description="ID of the vendor as a string")
    product_id: str = Field(..., description="ID of the product as a string")
    quantity: int = Field(..., description="Quantity of the product")
    total_price: float = Field(..., description="Total price of the order in IRR")
    status: str = Field(..., description="Status of the order")
    shipping_address: Optional[str] = Field(None, description="Shipping address")
    notes: Optional[str] = Field(None, description="Notes for the order")
    payment_status: str = Field(..., description="Payment status")
    payment_method: Optional[str] = Field(None, description="Payment method used")
    created_at: datetime = Field(..., description="Creation time (UTC)")
    updated_at: datetime = Field(..., description="Last update time (UTC)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

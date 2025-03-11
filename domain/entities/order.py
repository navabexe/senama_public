# domain/entities/order.py
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, validator


class Order(BaseModel):
    """Entity representing an order in the marketplace."""
    id: Optional[str] = Field(None, description="Unique identifier of the order as a string")
    user_id: str = Field(..., description="ID of the user placing the order as a string")
    vendor_id: str = Field(..., description="ID of the vendor fulfilling the order as a string")
    product_id: str = Field(..., description="ID of the product being ordered as a string")
    quantity: int = Field(..., ge=1, description="Quantity of the product ordered, must be positive")
    total_price: float = Field(..., ge=0, description="Total price of the order in IRR, must be non-negative")
    status: str = Field("pending", description="Status of the order (pending/accepted/delivered/cancelled)")
    shipping_address: Optional[str] = Field(None, description="Shipping address for the order")
    notes: Optional[str] = Field(None, description="Optional notes for the order")
    payment_status: str = Field("unpaid", description="Payment status (unpaid/paid/failed)")
    payment_method: Optional[str] = Field(None, description="Payment method used (e.g., card, cash)")
    tracking_info: Optional[dict] = Field(None, description="Tracking information for the order")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 description="Last update time (UTC)")

    @validator("id", "user_id", "vendor_id", "product_id", pre=True)
    def validate_id_format(cls, value):
        """Validate that ID fields are valid strings."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"ID must be a non-empty string, got: {value}")
        return value

    @validator("status")
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ["pending", "accepted", "delivered", "cancelled"]
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {value}")
        return value

    @validator("payment_status")
    def validate_payment_status(cls, value):
        """Ensure payment_status is valid."""
        valid_payment_statuses = ["unpaid", "paid", "failed"]
        if value not in valid_payment_statuses:
            raise ValueError(f"Payment status must be one of {valid_payment_statuses}, got: {value}")
        return value

    @validator("shipping_address", "notes", "payment_method")
    def validate_optional_strings(cls, value):
        """Ensure optional string fields are valid if provided."""
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Field must be a non-empty string if provided")
        return value

    @validator("tracking_info")
    def validate_tracking_info(cls, value):
        """Ensure tracking_info is a dictionary if provided."""
        if value is not None and not isinstance(value, dict):
            raise ValueError("tracking_info must be a dictionary if provided")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

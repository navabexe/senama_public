# core/utils/validation.py
from typing import Any, Dict
from bson import ObjectId
from core.errors import ValidationError

def validate_object_id(value: str, field_name: str) -> None:
    """Validate that a string is a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(value):
        raise ValidationError(f"Invalid {field_name} format: {value}")

def validate_required_fields(data: Dict[str, Any], required_fields: list[str]) -> None:
    """Validate that all required fields are present and non-empty."""
    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"{field} is required")
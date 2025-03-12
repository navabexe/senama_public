# domain/schemas/upload.py
from pydantic import BaseModel, field_validator


class UploadMetadata(BaseModel):
    user_id: str
    entity_type: str
    entity_id: str

    @field_validator("entity_type")
    def validate_entity_type(cls, value):
        if value not in ["user", "vendor", "product"]:
            raise ValueError("Entity type must be 'user', 'vendor', or 'product'")
        return value
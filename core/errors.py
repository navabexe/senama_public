# core/errors.py
from fastapi import HTTPException

class BaseError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundError(BaseError):
    def __init__(self, detail: str = "Item not found"):
        super().__init__(status_code=404, detail=detail)

class ValidationError(BaseError):
    def __init__(self, detail: str = "Invalid input"):
        super().__init__(status_code=400, detail=detail)

class UnauthorizedError(BaseError):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=401, detail=detail)

class InternalServerError(BaseError):
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status_code=500, detail=detail)

# routes/v1/business_categories.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.business_categories import create_business_category, get_business_category, update_business_category, delete_business_category
from domain.schemas.business_category import BusinessCategoryCreate, BusinessCategoryUpdate, BusinessCategoryResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new business category", description="Creates a new business category (admin only).")
@limiter.limit("5/minute")
async def create_business_category_route(request: Request, category_data: BusinessCategoryCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "admin" not in current_user["roles"]:
        raise UnauthorizedError("Only admins can create categories")
    return create_business_category(db, category_data.dict())

@router.get("/{category_id}", response_model=BusinessCategoryResponse, summary="Get business category by ID", description="Retrieves a business category by its ID.")
@limiter.limit("10/minute")
async def get_business_category_route(request: Request, category_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)  # احراز هویت
    return get_business_category(db, category_id)

@router.put("/{category_id}", response_model=BusinessCategoryResponse, summary="Update business category", description="Updates a business category (admin only).")
@limiter.limit("5/minute")
async def update_business_category_route(request: Request, category_id: str, update_data: BusinessCategoryUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "admin" not in current_user["roles"]:
        raise UnauthorizedError("Only admins can update categories")
    return update_business_category(db, category_id, update_data.dict(exclude_unset=True))

@router.delete("/{category_id}", response_model=dict, summary="Delete business category", description="Deletes a business category (admin only).")
@limiter.limit("5/minute")
async def delete_business_category_route(request: Request, category_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "admin" not in current_user["roles"]:
        raise UnauthorizedError("Only admins can delete categories")
    return delete_business_category(db, category_id)
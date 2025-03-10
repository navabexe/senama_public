# routes/v1/product_categories.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.product_categories import create_product_category, get_product_category, update_product_category, delete_product_category
from domain.schemas.product_category import ProductCategoryCreate, ProductCategoryUpdate, ProductCategoryResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new product category", description="Creates a new product category (admin only).")
@limiter.limit("5/minute")
async def create_product_category_route(request: Request, category_data: ProductCategoryCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "admin" not in current_user["roles"]:
        raise UnauthorizedError("Only admins can create categories")
    return create_product_category(db, category_data.dict())

@router.get("/{category_id}", response_model=ProductCategoryResponse, summary="Get product category by ID", description="Retrieves a product category by its ID.")
@limiter.limit("10/minute")
async def get_product_category_route(request: Request, category_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)  # احراز هویت
    return get_product_category(db, category_id)

@router.put("/{category_id}", response_model=ProductCategoryResponse, summary="Update product category", description="Updates a product category (admin only).")
@limiter.limit("5/minute")
async def update_product_category_route(request: Request, category_id: str, update_data: ProductCategoryUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "admin" not in current_user["roles"]:
        raise UnauthorizedError("Only admins can update categories")
    return update_product_category(db, category_id, update_data.dict(exclude_unset=True))

@router.delete("/{category_id}", response_model=dict, summary="Delete product category", description="Deletes a product category (admin only).")
@limiter.limit("5/minute")
async def delete_product_category_route(request: Request, category_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "admin" not in current_user["roles"]:
        raise UnauthorizedError("Only admins can delete categories")
    return delete_product_category(db, category_id)
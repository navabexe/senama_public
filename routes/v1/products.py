# routes/v1/products.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.products import create_product, get_product, update_product, delete_product
from domain.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new product", description="Creates a new product for the authenticated vendor.")
@limiter.limit("5/minute")
async def create_product_route(request: Request, product_data: ProductCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can create products")
    return create_product(db, str(current_user["_id"]), product_data.dict())

@router.get("/{product_id}", response_model=ProductResponse, summary="Get product by ID", description="Retrieves a product by its ID.")
@limiter.limit("10/minute")
async def get_product_route(request: Request, product_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_product(db, product_id)

@router.put("/{product_id}", response_model=ProductResponse, summary="Update product", description="Updates product details for the authenticated vendor.")
@limiter.limit("5/minute")
async def update_product_route(request: Request, product_id: str, update_data: ProductUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can update products")
    return update_product(db, product_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{product_id}", response_model=dict, summary="Delete product", description="Deletes a product by its ID for the authenticated vendor.")
@limiter.limit("5/minute")
async def delete_product_route(request: Request, product_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can delete products")
    return delete_product(db, product_id, str(current_user["_id"]))
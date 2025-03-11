# routes/v1/products.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from infrastructure.database.client import get_db
from services.products import create_product, get_product, get_products_by_vendor, update_product, delete_product
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new product")
@limiter.limit("5/minute")
async def create_product_route(
    request: Request,
    product_data: ProductCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Create a new product (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can create products")
        vendor_id = str(current_user["_id"])
        result = create_product(db, vendor_id, product_data.model_dump())
        logger.info(f"Product created by vendor {vendor_id}: {result['id']}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to create product: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{product_id}", response_model=ProductResponse, summary="Get product by ID")
@limiter.limit("10/minute")
async def get_product_route(
    request: Request,
    product_id: str,
    db: Database = Depends(get_db)
):
    """Get a product by ID (public access)."""
    try:
        product = get_product(db, product_id)
        logger.info(f"Product retrieved: {product_id}")
        return product
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve product {product_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/vendor/{vendor_id}", response_model=list[ProductResponse], summary="Get all products by vendor")
@limiter.limit("10/minute")
async def get_vendor_products_route(
    request: Request,
    vendor_id: str,
    db: Database = Depends(get_db)
):
    """Get all products for a specific vendor (public access)."""
    try:
        products = get_products_by_vendor(db, vendor_id)
        logger.info(f"Retrieved {len(products)} products for vendor: {vendor_id}")
        return products
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve products for vendor {vendor_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{product_id}", response_model=ProductResponse, summary="Update product")
@limiter.limit("5/minute")
async def update_product_route(
    request: Request,
    product_id: str,
    update_data: ProductUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Update a product (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can update products")
        vendor_id = str(current_user["_id"])
        product = update_product(db, product_id, vendor_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Product updated: {product_id} by vendor: {vendor_id}")
        return product
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to update product {product_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{product_id}", response_model=dict, summary="Delete product")
@limiter.limit("5/minute")
async def delete_product_route(
    request: Request,
    product_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Delete a product (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can delete products")
        vendor_id = str(current_user["_id"])
        result = delete_product(db, product_id, vendor_id)
        logger.info(f"Product deleted: {product_id} by vendor: {vendor_id}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to delete product {product_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
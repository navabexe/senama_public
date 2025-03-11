# routes/v1/product_categories.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.product_category import ProductCategoryCreate, ProductCategoryUpdate, ProductCategoryResponse
from infrastructure.database.client import get_db
from services.product_categories import create_product_category, get_product_category, get_all_product_categories, update_product_category, delete_product_category
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new product category")
@limiter.limit("5/minute")
async def create_product_category_route(
    request: Request,
    category_data: ProductCategoryCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can create product categories")
        result = create_product_category(db, category_data.model_dump())
        logger.info(f"Product category created by admin {current_user['_id']}: {result['id']}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to create product category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{category_id}", response_model=ProductCategoryResponse, summary="Get product category by ID")
@limiter.limit("10/minute")
async def get_product_category_route(
    request: Request,
    category_id: str,
    db: Database = Depends(get_db)
):
    try:
        category = get_product_category(db, category_id)
        logger.info(f"Product category retrieved: {category_id}")
        return category
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve product category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=list[ProductCategoryResponse], summary="Get all product categories")
@limiter.limit("10/minute")
async def get_all_product_categories_route(
    request: Request,
    db: Database = Depends(get_db)
):
    try:
        categories = get_all_product_categories(db)
        logger.info(f"Retrieved {len(categories)} product categories")
        return categories
    except Exception as e:
        logger.error(f"Failed to retrieve all product categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{category_id}", response_model=ProductCategoryResponse, summary="Update product category")
@limiter.limit("5/minute")
async def update_product_category_route(
    request: Request,
    category_id: str,
    update_data: ProductCategoryUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can update product categories")
        category = update_product_category(db, category_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Product category updated: {category_id} by admin: {current_user['_id']}")
        return category
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
        logger.error(f"Failed to update product category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{category_id}", response_model=dict, summary="Delete product category")
@limiter.limit("5/minute")
async def delete_product_category_route(
    request: Request,
    category_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can delete product categories")
        result = delete_product_category(db, category_id)
        logger.info(f"Product category deleted: {category_id} by admin: {current_user['_id']}")
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
        logger.error(f"Failed to delete product category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
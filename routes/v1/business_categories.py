# routes/v1/business_categories.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.business_category import BusinessCategoryCreate, BusinessCategoryUpdate, BusinessCategoryResponse
from infrastructure.database.client import get_db
from services.business_categories import create_business_category, get_business_category, get_all_business_categories, update_business_category, delete_business_category
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new business category")
@limiter.limit("5/minute")
async def create_business_category_route(
    request: Request,
    category_data: BusinessCategoryCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Create a new business category (admin only)."""
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can create business categories")
        result = create_business_category(db, category_data.model_dump())
        logger.info(f"Business category created by admin {current_user['_id']}: {result['id']}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to create business category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{category_id}", response_model=BusinessCategoryResponse, summary="Get business category by ID")
@limiter.limit("10/minute")
async def get_business_category_route(
    request: Request,
    category_id: str,
    db: Database = Depends(get_db)
):
    """Get a business category by ID (public access)."""
    try:
        category = get_business_category(db, category_id)
        logger.info(f"Business category retrieved: {category_id}")
        return category
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve business category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=list[BusinessCategoryResponse], summary="Get all business categories")
@limiter.limit("10/minute")
async def get_all_business_categories_route(
    request: Request,
    db: Database = Depends(get_db)
):
    """Get all business categories (public access)."""
    try:
        categories = get_all_business_categories(db)
        logger.info(f"Retrieved {len(categories)} business categories")
        return categories
    except Exception as e:
        logger.error(f"Failed to retrieve all business categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{category_id}", response_model=BusinessCategoryResponse, summary="Update business category")
@limiter.limit("5/minute")
async def update_business_category_route(
    request: Request,
    category_id: str,
    update_data: BusinessCategoryUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Update a business category (admin only)."""
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can update business categories")
        category = update_business_category(db, category_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Business category updated: {category_id} by admin: {current_user['_id']}")
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
        logger.error(f"Failed to update business category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{category_id}", response_model=dict, summary="Delete business category")
@limiter.limit("5/minute")
async def delete_business_category_route(
    request: Request,
    category_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Delete a business category (admin only)."""
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can delete business categories")
        result = delete_business_category(db, category_id)
        logger.info(f"Business category deleted: {category_id} by admin: {current_user['_id']}")
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
        logger.error(f"Failed to delete business category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
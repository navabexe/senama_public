# routes/v1/vendors.py
import logging

from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse
from infrastructure.database.client import get_db
from services.vendors import create_vendor, get_vendor, update_vendor, delete_vendor

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.post("", response_model=dict, summary="Create a new vendor")
@limiter.limit("5/minute")
async def create_vendor_route(
        request: Request,
        vendor_data: VendorCreate,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Create a new vendor (accessible by anyone, pending verification)."""
    try:
        # اینجا نیازی به احراز هویت نیست چون ثبت‌نام اولیه آزاده
        result = create_vendor(db, vendor_data.model_dump())
        logger.info(f"Vendor creation initiated: {result['id']}")
        return result
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to create vendor: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{vendor_id}", response_model=VendorResponse, summary="Get vendor by ID")
@limiter.limit("10/minute")
async def get_vendor_route(
        request: Request,
        vendor_id: str,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Get a vendor by ID (vendor or admin only)."""
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        vendor = get_vendor(db, vendor_id, requester_id)
        logger.info(f"Vendor retrieved: {vendor_id} by requester: {requester_id}")
        return vendor
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
        logger.error(f"Failed to retrieve vendor {vendor_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{vendor_id}", response_model=VendorResponse, summary="Update vendor")
@limiter.limit("5/minute")
async def update_vendor_route(
        request: Request,
        vendor_id: str,
        update_data: VendorUpdate,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Update a vendor (vendor or admin only)."""
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        vendor = update_vendor(db, vendor_id, requester_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Vendor updated: {vendor_id} by requester: {requester_id}")
        return vendor
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
        logger.error(f"Failed to update vendor {vendor_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{vendor_id}", response_model=dict, summary="Delete vendor")
@limiter.limit("5/minute")
async def delete_vendor_route(
        request: Request,
        vendor_id: str,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Delete a vendor (vendor or admin only)."""
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        result = delete_vendor(db, vendor_id, requester_id)
        logger.info(f"Vendor deleted: {vendor_id} by requester: {requester_id}")
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
        logger.error(f"Failed to delete vendor {vendor_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

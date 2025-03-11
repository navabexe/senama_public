# routes/v1/admin.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.user import UserResponse
from domain.schemas.vendor import VendorResponse
from infrastructure.database.client import get_db
from services.users import get_user
from services.vendors import get_vendor
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.get("/users", response_model=list[UserResponse], summary="Get all users")
@limiter.limit("10/minute")
async def get_all_users_route(
    request: Request,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can view all users")
        users = list(db.users.find())
        logger.info(f"Retrieved {len(users)} users by admin {current_user['_id']}")
        return [UserResponse(**user) for user in users]
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/vendors", response_model=list[VendorResponse], summary="Get all vendors")
@limiter.limit("10/minute")
async def get_all_vendors_route(
    request: Request,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can view all vendors")
        vendors = list(db.vendors.find())
        logger.info(f"Retrieved {len(vendors)} vendors by admin {current_user['_id']}")
        return [VendorResponse(**vendor) for vendor in vendors]
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve vendors: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/users/{user_id}", response_model=UserResponse, summary="Get user by ID (admin)")
@limiter.limit("10/minute")
async def get_user_admin_route(
    request: Request,
    user_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can view user details")
        requester_id = str(current_user["_id"])
        user = get_user(db, user_id, requester_id)
        logger.info(f"User retrieved: {user_id} by admin: {requester_id}")
        return user
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
        logger.error(f"Failed to retrieve user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/vendors/{vendor_id}", response_model=VendorResponse, summary="Get vendor by ID (admin)")
@limiter.limit("10/minute")
async def get_vendor_admin_route(
    request: Request,
    vendor_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can view vendor details")
        requester_id = str(current_user["_id"])
        vendor = get_vendor(db, vendor_id, requester_id)
        logger.info(f"Vendor retrieved: {vendor_id} by admin: {requester_id}")
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
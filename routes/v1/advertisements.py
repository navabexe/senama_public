# routes/v1/advertisements.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.advertisement import AdvertisementCreate, AdvertisementUpdate, AdvertisementResponse
from infrastructure.database.client import get_db
from services.advertisements import create_advertisement, get_advertisement, get_advertisements_by_vendor, update_advertisement, delete_advertisement
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new advertisement")
@limiter.limit("5/minute")
async def create_advertisement_route(
    request: Request,
    advertisement_data: AdvertisementCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can create advertisements")
        vendor_id = str(current_user["_id"])
        result = create_advertisement(db, vendor_id, advertisement_data.model_dump())
        logger.info(f"Advertisement created by vendor {vendor_id}: {result['id']}")
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
        logger.error(f"Failed to create advertisement: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{advertisement_id}", response_model=AdvertisementResponse, summary="Get advertisement by ID")
@limiter.limit("10/minute")
async def get_advertisement_route(
    request: Request,
    advertisement_id: str,
    db: Database = Depends(get_db)
):
    try:
        advertisement = get_advertisement(db, advertisement_id)
        logger.info(f"Advertisement retrieved: {advertisement_id}")
        return advertisement
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve advertisement {advertisement_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/vendor/{vendor_id}", response_model=list[AdvertisementResponse], summary="Get all advertisements by vendor")
@limiter.limit("10/minute")
async def get_vendor_advertisements_route(
    request: Request,
    vendor_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        if requester_id != vendor_id and "admin" not in current_user["roles"]:
            raise UnauthorizedError("You can only view your own advertisements unless you are an admin")
        advertisements = get_advertisements_by_vendor(db, vendor_id)
        logger.info(f"Retrieved {len(advertisements)} advertisements for vendor: {vendor_id}")
        return advertisements
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve advertisements for vendor {vendor_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{advertisement_id}", response_model=AdvertisementResponse, summary="Update advertisement")
@limiter.limit("5/minute")
async def update_advertisement_route(
    request: Request,
    advertisement_id: str,
    update_data: AdvertisementUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can update advertisements")
        vendor_id = str(current_user["_id"])
        advertisement = update_advertisement(db, advertisement_id, vendor_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Advertisement updated: {advertisement_id} by vendor: {vendor_id}")
        return advertisement
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
        logger.error(f"Failed to update advertisement {advertisement_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{advertisement_id}", response_model=dict, summary="Delete advertisement")
@limiter.limit("5/minute")
async def delete_advertisement_route(
    request: Request,
    advertisement_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can delete advertisements")
        vendor_id = str(current_user["_id"])
        result = delete_advertisement(db, advertisement_id, vendor_id)
        logger.info(f"Advertisement deleted: {advertisement_id} by vendor: {vendor_id}")
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
        logger.error(f"Failed to delete advertisement {advertisement_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
# routes/v1/advertisements.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.advertisements import create_advertisement, get_advertisement, update_advertisement, delete_advertisement
from domain.schemas.advertisement import AdvertisementCreate, AdvertisementUpdate, AdvertisementResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new advertisement", description="Creates a new advertisement for the authenticated vendor.")
@limiter.limit("5/minute")
async def create_advertisement_route(request: Request, ad_data: AdvertisementCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can create advertisements")
    return create_advertisement(db, str(current_user["_id"]), ad_data.dict())

@router.get("/{ad_id}", response_model=AdvertisementResponse, summary="Get advertisement by ID", description="Retrieves an advertisement by its ID for the authenticated vendor.")
@limiter.limit("10/minute")
async def get_advertisement_route(request: Request, ad_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can view advertisements")
    return get_advertisement(db, ad_id, str(current_user["_id"]))

@router.put("/{ad_id}", response_model=AdvertisementResponse, summary="Update advertisement", description="Updates advertisement status or details for the authenticated vendor.")
@limiter.limit("5/minute")
async def update_advertisement_route(request: Request, ad_id: str, update_data: AdvertisementUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can update advertisements")
    return update_advertisement(db, ad_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{ad_id}", response_model=dict, summary="Delete advertisement", description="Deletes a pending advertisement for the authenticated vendor.")
@limiter.limit("5/minute")
async def delete_advertisement_route(request: Request, ad_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can delete advertisements")
    return delete_advertisement(db, ad_id, str(current_user["_id"]))
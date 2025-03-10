# routes/v1/vendors.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.vendors import create_vendor, get_vendor, update_vendor, delete_vendor
from domain.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new vendor", description="Creates a new vendor with the provided data. Status will be 'pending' until approved.")
@limiter.limit("5/minute")
async def create_vendor_route(request: Request, vendor_data: VendorCreate, db: Database = Depends(get_db)):
    return create_vendor(db, vendor_data.dict())

@router.get("/{vendor_id}", response_model=VendorResponse, summary="Get vendor by ID", description="Retrieves a vendor by their ID.")
@limiter.limit("10/minute")
async def get_vendor_route(request: Request, vendor_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_vendor(db, vendor_id)

@router.put("/{vendor_id}", response_model=VendorResponse, summary="Update vendor", description="Updates vendor details.")
@limiter.limit("5/minute")
async def update_vendor_route(request: Request, vendor_id: str, update_data: VendorUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"] or str(current_user["_id"]) != vendor_id:
        raise UnauthorizedError("You can only update your own vendor profile")
    return update_vendor(db, vendor_id, update_data.dict(exclude_unset=True))

@router.delete("/{vendor_id}", response_model=dict, summary="Delete vendor", description="Deletes a vendor by their ID.")
@limiter.limit("5/minute")
async def delete_vendor_route(request: Request, vendor_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"] or str(current_user["_id"]) != vendor_id:
        raise UnauthorizedError("You can only delete your own vendor profile")
    return delete_vendor(db, vendor_id)
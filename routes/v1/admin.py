# routes/v1/admin.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.admin import AdminService
from domain.schemas.vendor import VendorResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.put("/verify-vendor/{vendor_id}", response_model=VendorResponse, summary="Verify a vendor", description="Updates vendor status to 'active' or 'rejected' by an admin.")
@limiter.limit("5/minute")
async def verify_vendor_route(
    request: Request,
    vendor_id: str,
    status: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    current_user = get_current_user(token, db)
    admin_service = AdminService(db)
    return admin_service.verify_vendor(str(current_user["_id"]), vendor_id, status)

@router.put("/deactivate/{target_type}/{target_id}", response_model=dict, summary="Deactivate an account", description="Deactivates a user or vendor account by an admin.")
@limiter.limit("5/minute")
async def deactivate_account_route(
    request: Request,
    target_type: str,
    target_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    current_user = get_current_user(token, db)
    admin_service = AdminService(db)
    return admin_service.deactivate_account(str(current_user["_id"]), target_id, target_type)

@router.delete("/delete/{target_type}/{target_id}", response_model=dict, summary="Delete an account", description="Deletes a user or vendor account by an admin.")
@limiter.limit("5/minute")
async def delete_account_route(
    request: Request,
    target_type: str,
    target_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    current_user = get_current_user(token, db)
    admin_service = AdminService(db)
    return admin_service.delete_account(str(current_user["_id"]), target_id, target_type)
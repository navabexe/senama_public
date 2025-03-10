# routes/v1/notifications.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.notifications import create_notification, get_notification, update_notification, delete_notification
from domain.schemas.notification import NotificationCreate, NotificationUpdate, NotificationResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new notification", description="Creates a new notification for a user or vendor (admin only).")
@limiter.limit("5/minute")
async def create_notification_route(request: Request, notification_data: NotificationCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "admin" not in current_user["roles"]:
        raise UnauthorizedError("Only admins can create notifications")
    return create_notification(db, notification_data.dict())

@router.get("/{notification_id}", response_model=NotificationResponse, summary="Get notification by ID", description="Retrieves a notification by its ID for the authenticated user or vendor.")
@limiter.limit("10/minute")
async def get_notification_route(request: Request, notification_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_notification(db, notification_id, str(current_user["_id"]))

@router.put("/{notification_id}", response_model=NotificationResponse, summary="Update notification", description="Updates notification status (e.g., mark as read) for the authenticated user or vendor.")
@limiter.limit("5/minute")
async def update_notification_route(request: Request, notification_id: str, update_data: NotificationUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return update_notification(db, notification_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{notification_id}", response_model=dict, summary="Delete notification", description="Deletes a notification by its ID for the authenticated user or vendor.")
@limiter.limit("5/minute")
async def delete_notification_route(request: Request, notification_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return delete_notification(db, notification_id, str(current_user["_id"]))
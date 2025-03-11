# routes/v1/notifications.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.notification import NotificationCreate, NotificationUpdate, NotificationResponse
from infrastructure.database.client import get_db
from services.notifications import create_notification, get_notification, get_notifications_by_user, update_notification, delete_notification
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new notification")
@limiter.limit("5/minute")
async def create_notification_route(
    request: Request,
    notification_data: NotificationCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can create notifications")
        result = create_notification(db, notification_data.model_dump())
        logger.info(f"Notification created by admin {current_user['_id']}: {result['id']}")
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
        logger.error(f"Failed to create notification: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{notification_id}", response_model=NotificationResponse, summary="Get notification by ID")
@limiter.limit("10/minute")
async def get_notification_route(
    request: Request,
    notification_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        notification = get_notification(db, notification_id, user_id)
        logger.info(f"Notification retrieved: {notification_id} by user: {user_id}")
        return notification
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
        logger.error(f"Failed to retrieve notification {notification_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/user/{user_id}", response_model=list[NotificationResponse], summary="Get all notifications by user")
@limiter.limit("10/minute")
async def get_user_notifications_route(
    request: Request,
    user_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        if requester_id != user_id and "admin" not in current_user["roles"]:
            raise UnauthorizedError("You can only view your own notifications unless you are an admin")
        notifications = get_notifications_by_user(db, user_id)
        logger.info(f"Retrieved {len(notifications)} notifications for user: {user_id}")
        return notifications
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve notifications for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{notification_id}", response_model=NotificationResponse, summary="Update notification")
@limiter.limit("5/minute")
async def update_notification_route(
    request: Request,
    notification_id: str,
    update_data: NotificationUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        notification = update_notification(db, notification_id, user_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Notification updated: {notification_id} by user: {user_id}")
        return notification
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
        logger.error(f"Failed to update notification {notification_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{notification_id}", response_model=dict, summary="Delete notification")
@limiter.limit("5/minute")
async def delete_notification_route(
    request: Request,
    notification_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        result = delete_notification(db, notification_id, user_id)
        logger.info(f"Notification deleted: {notification_id} by user: {user_id}")
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
        logger.error(f"Failed to delete notification {notification_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
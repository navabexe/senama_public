# services/notifications.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.notification import Notification
from domain.schemas.notification import NotificationCreate, NotificationUpdate

logger = logging.getLogger(__name__)

def create_notification(db: Database, notification_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new notification with atomic check to prevent duplicates.

    Args:
        db (Database): MongoDB database instance.
        notification_data (Dict[str, Any]): Data for the notification including type, message, user_id, and/or vendor_id.

    Returns:
        Dict[str, str]: Dictionary containing the created notification ID.

    Raises:
        ValidationError: If required fields are missing or invalid, or if notification already exists.
        NotFoundError: If user or vendor is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        notification_create = NotificationCreate(**notification_data)  # اعتبارسنجی با Pydantic
        notification_data_validated = notification_create.model_dump()

        if notification_data_validated.get("user_id"):
            validate_object_id(notification_data_validated["user_id"], "user_id")
            if not db.users.find_one({"_id": ObjectId(notification_data_validated["user_id"])}):
                raise NotFoundError(f"User with ID {notification_data_validated['user_id']} not found")
        if notification_data_validated.get("vendor_id"):
            validate_object_id(notification_data_validated["vendor_id"], "vendor_id")
            if not db.vendors.find_one({"_id": ObjectId(notification_data_validated["vendor_id"])}):
                raise NotFoundError(f"Vendor with ID {notification_data_validated['vendor_id']} not found")

        notification = Notification(**notification_data_validated)

        with db.client.start_session() as session:
            with session.start_transaction():
                # بررسی اتمی برای جلوگیری از اعلان تکراری
                query = {
                    "type": notification_data_validated["type"],
                    "user_id": notification_data_validated.get("user_id"),
                    "vendor_id": notification_data_validated.get("vendor_id"),
                    "related_id": notification_data_validated.get("related_id")
                }
                existing_notification = db.notifications.find_one(query, session=session)
                if existing_notification:
                    raise ValidationError("A notification with this type and related ID already exists for this user/vendor")

                result = db.notifications.insert_one(notification.model_dump(exclude={"id"}), session=session)
                notification_id = str(result.inserted_id)

        logger.info(f"Notification created with ID: {notification_id}")
        return {"id": notification_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_notification: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_notification: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_notification: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create notification: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_notification: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create notification: {str(e)}")

def get_notification(db: Database, notification_id: str, user_id: str) -> Notification:
    """Retrieve a notification by its ID.

    Args:
        db (Database): MongoDB database instance.
        notification_id (str): ID of the notification to retrieve.
        user_id (str): ID of the user or vendor requesting the notification.

    Returns:
        Notification: The requested notification object.

    Raises:
        ValidationError: If notification_id or user_id is invalid.
        NotFoundError: If notification is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(notification_id, "notification_id")
        validate_object_id(user_id, "user_id")

        notification = db.notifications.find_one({"_id": ObjectId(notification_id)})
        if not notification:
            raise NotFoundError(f"Notification with ID {notification_id} not found")
        if notification.get("user_id") != user_id and notification.get("vendor_id") != user_id:
            raise UnauthorizedError("You can only view your own notifications")

        logger.info(f"Notification retrieved: {notification_id}")
        return Notification(**notification)
    except ValidationError as ve:
        logger.error(f"Validation error in get_notification: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_notification: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_notification: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_notification: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get notification: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_notification: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get notification: {str(e)}")

def get_notifications_by_user(db: Database, user_id: str) -> List[Notification]:
    """Retrieve all notifications for a specific user or vendor.

    Args:
        db (Database): MongoDB database instance.
        user_id (str): ID of the user or vendor to retrieve notifications for.

    Returns:
        List[Notification]: List of notification objects.

    Raises:
        ValidationError: If user_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(user_id, "user_id")

        notifications = list(db.notifications.find({
            "$or": [
                {"user_id": user_id},
                {"vendor_id": user_id}
            ]
        }))
        if not notifications:
            logger.debug(f"No notifications found for user_id: {user_id}")
            return []

        logger.info(f"Retrieved {len(notifications)} notifications for user: {user_id}")
        return [Notification(**notification) for notification in notifications]
    except ValidationError as ve:
        logger.error(f"Validation error in get_notifications_by_user: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_notifications_by_user: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get notifications: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_notifications_by_user: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get notifications: {str(e)}")

def update_notification(db: Database, notification_id: str, user_id: str, update_data: Dict[str, Any]) -> Notification:
    """Update an existing notification.

    Args:
        db (Database): MongoDB database instance.
        notification_id (str): ID of the notification to update.
        user_id (str): ID of the user or vendor updating the notification.
        update_data (Dict[str, Any]): Data to update in the notification (e.g., status).

    Returns:
        Notification: The updated notification object.

    Raises:
        ValidationError: If notification_id, user_id, or status is invalid.
        NotFoundError: If notification is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(notification_id, "notification_id")
        validate_object_id(user_id, "user_id")
        notification_update = NotificationUpdate(**update_data)
        update_data_validated = notification_update.model_dump(exclude_unset=True)

        notification = db.notifications.find_one({"_id": ObjectId(notification_id)})
        if not notification:
            raise NotFoundError(f"Notification with ID {notification_id} not found")
        if notification.get("user_id") != user_id and notification.get("vendor_id") != user_id:
            raise UnauthorizedError("You can only update your own notifications")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)
        updated = db.notifications.update_one({"_id": ObjectId(notification_id)}, {"$set": update_data_validated})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update notification {notification_id}")

        updated_notification = db.notifications.find_one({"_id": ObjectId(notification_id)})
        logger.info(f"Notification updated: {notification_id}")
        return Notification(**updated_notification)
    except ValidationError as ve:
        logger.error(f"Validation error in update_notification: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_notification: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_notification: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_notification: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update notification: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_notification: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update notification: {str(e)}")

def delete_notification(db: Database, notification_id: str, user_id: str) -> Dict[str, str]:
    """Delete a notification.

    Args:
        db (Database): MongoDB database instance.
        notification_id (str): ID of the notification to delete.
        user_id (str): ID of the user or vendor deleting the notification.

    Returns:
        Dict[str, str]: Confirmation message of deletion.

    Raises:
        ValidationError: If notification_id or user_id is invalid.
        NotFoundError: If notification is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(notification_id, "notification_id")
        validate_object_id(user_id, "user_id")

        notification = db.notifications.find_one({"_id": ObjectId(notification_id)})
        if not notification:
            raise NotFoundError(f"Notification with ID {notification_id} not found")
        if notification.get("user_id") != user_id and notification.get("vendor_id") != user_id:
            raise UnauthorizedError("You can only delete your own notifications")

        db.notifications.delete_one({"_id": ObjectId(notification_id)})
        logger.info(f"Notification deleted: {notification_id}")
        return {"message": f"Notification {notification_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_notification: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_notification: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_notification: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_notification: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete notification: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_notification: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete notification: {str(e)}")
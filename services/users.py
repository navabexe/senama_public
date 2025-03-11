# services/users.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, InternalServerError, UnauthorizedError
from core.utils.db import DBHelper
from domain.entities.user import User

logger = logging.getLogger(__name__)


def create_user(db: Database, user_data: dict) -> dict:
    """Create a new user.

    Args:
        db (Database): MongoDB database instance.
        user_data (dict): Data for the user including phone number.

    Returns:
        dict: Dictionary containing the created user ID.

    Raises:
        ValidationError: If required fields are missing or invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    db_helper = DBHelper()
    try:
        if not user_data.get("phone"):
            raise ValidationError("Phone number is required")
        if db_helper.find_one("users", {"phone": user_data["phone"]}):
            raise ValidationError("Phone number already registered")

        user = User(**user_data)
        user_id = db_helper.insert_one("users", user.model_dump(exclude={"id"}))
        logger.info(f"User created with ID: {user_id}")
        return {"id": user_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_user: {ve.detail}")
        raise ve
    except DuplicateKeyError:
        logger.error("Duplicate user detected")
        raise ValidationError("A user with this phone number already exists")
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_user: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create user: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_user: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create user: {str(e)}")


def get_user(db: Database, user_id: str, requester_id: str = None) -> User:
    """Retrieve a user by their ID.

    Args:
        db (Database): MongoDB database instance.
        user_id (str): ID of the user to retrieve.
        requester_id (str, optional): ID of the user requesting the data, for authorization check.

    Returns:
        User: The requested user object.

    Raises:
        ValidationError: If user_id format is invalid.
        NotFoundError: If user is not found.
        UnauthorizedError: If requester is not authorized (when applicable).
        InternalServerError: For unexpected errors or database failures.
    """
    db_helper = DBHelper()
    try:
        if not ObjectId.is_valid(user_id):
            raise ValidationError(f"Invalid user ID format: {user_id}")

        user = db_helper.find_one("users", {"_id": ObjectId(user_id)})
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        # اگر requester_id داده شده باشه، بررسی دسترسی
        if requester_id and not ObjectId.is_valid(requester_id):
            raise ValidationError(f"Invalid requester_id format: {requester_id}")
        if requester_id and requester_id != user_id:
            requester = db_helper.find_one("users", {"_id": ObjectId(requester_id)})
            if not requester or "admin" not in requester.get("roles", []):
                raise UnauthorizedError("You can only view your own profile unless you are an admin")

        logger.info(f"User retrieved: {user_id}")
        return User(**user)
    except ValidationError as ve:
        logger.error(f"Validation error in get_user: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_user: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_user: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_user: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get user: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_user: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get user: {str(e)}")


def update_user(db: Database, user_id: str, requester_id: str, update_data: dict) -> User:
    """Update an existing user.

    Args:
        db (Database): MongoDB database instance.
        user_id (str): ID of the user to update.
        requester_id (str): ID of the user requesting the update.
        update_data (dict): Data to update in the user.

    Returns:
        User: The updated user object.

    Raises:
        ValidationError: If user_id or requester_id is invalid.
        NotFoundError: If user is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    db_helper = DBHelper()
    try:
        if not ObjectId.is_valid(user_id):
            raise ValidationError(f"Invalid user ID format: {user_id}")
        if not ObjectId.is_valid(requester_id):
            raise ValidationError(f"Invalid requester_id format: {requester_id}")

        user = db_helper.find_one("users", {"_id": ObjectId(user_id)})
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        if requester_id != user_id:
            requester = db_helper.find_one("users", {"_id": ObjectId(requester_id)})
            if not requester or "admin" not in requester.get("roles", []):
                raise UnauthorizedError("You can only update your own profile unless you are an admin")

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = db_helper.update_one("users", {"_id": ObjectId(user_id)}, update_data)
        if not updated:
            raise InternalServerError(f"Failed to update user {user_id}")

        updated_user = db_helper.find_one("users", {"_id": ObjectId(user_id)})
        logger.info(f"User updated: {user_id}")
        return User(**updated_user)
    except ValidationError as ve:
        logger.error(f"Validation error in update_user: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_user: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_user: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_user: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update user: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_user: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update user: {str(e)}")


def delete_user(db: Database, user_id: str, requester_id: str) -> dict:
    """Delete a user.

    Args:
        db (Database): MongoDB database instance.
        user_id (str): ID of the user to delete.
        requester_id (str): ID of the user requesting the deletion.

    Returns:
        dict: Confirmation message of deletion.

    Raises:
        ValidationError: If user_id or requester_id is invalid.
        NotFoundError: If user is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    db_helper = DBHelper()
    try:
        if not ObjectId.is_valid(user_id):
            raise ValidationError(f"Invalid user ID format: {user_id}")
        if not ObjectId.is_valid(requester_id):
            raise ValidationError(f"Invalid requester_id format: {requester_id}")

        user = db_helper.find_one("users", {"_id": ObjectId(user_id)})
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        if requester_id != user_id:
            requester = db_helper.find_one("users", {"_id": ObjectId(requester_id)})
            if not requester or "admin" not in requester.get("roles", []):
                raise UnauthorizedError("You can only delete your own account unless you are an admin")

        db_helper.get_collection("users").delete_one({"_id": ObjectId(user_id)})
        logger.info(f"User deleted: {user_id}")
        return {"message": f"User {user_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_user: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_user: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_user: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_user: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete user: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_user: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete user: {str(e)}")

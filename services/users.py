# services/users.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, InternalServerError, UnauthorizedError
from core.utils.validation import validate_object_id
from domain.entities.user import User
from domain.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)

class UserService:
    def __init__(cls, db: Database):
        """Initialize UserService with a database instance."""
        cls.db = db

    def create_user(cls, user_data: Dict[str, Any]) -> Dict[str, str]:
        """Create a new user with atomic check to prevent duplicates.

        Args:
            user_data (Dict[str, Any]): Data for the user including phone number.

        Returns:
            Dict[str, str]: Dictionary containing the created user ID.

        Raises:
            ValidationError: If required fields are missing, invalid, or phone is already registered.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            user_create = UserCreate(**user_data)  # اعتبارسنجی با Pydantic
            user_data_validated = user_create.model_dump()

            with cls.db.client.start_session() as session:
                with session.start_transaction():
                    # بررسی اتمی برای جلوگیری از ثبت کاربر تکراری
                    if cls.db.users.find_one({"phone": user_data_validated["phone"]}, session=session):
                        raise ValidationError("Phone number already registered")

                    user = User(**user_data_validated)
                    result = cls.db.users.insert_one(user.model_dump(exclude={"id"}), session=session)
                    user_id = str(result.inserted_id)

            logger.info(f"User created with ID: {user_id}")
            return {"id": user_id}
        except ValidationError as ve:
            logger.error(f"Validation error in create_user: {ve.detail}")
            raise ve
        except OperationFailure as of:
            logger.error(f"Database operation failed in create_user: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to create user: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in create_user: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to create user: {str(e)}")

    def get_user(cls, user_id: str, requester_id: str = None) -> User:
        """Retrieve a user by their ID.

        Args:
            user_id (str): ID of the user to retrieve.
            requester_id (str, optional): ID of the user requesting the data, for authorization check.

        Returns:
            User: The requested user object.

        Raises:
            ValidationError: If user_id or requester_id format is invalid.
            NotFoundError: If user is not found.
            UnauthorizedError: If requester is not authorized (when applicable).
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(user_id, "user_id")
            if requester_id:
                validate_object_id(requester_id, "requester_id")

            user = cls.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")

            if requester_id and requester_id != user_id:
                requester = cls.db.users.find_one({"_id": ObjectId(requester_id)})
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

    def update_user(cls, user_id: str, requester_id: str, update_data: Dict[str, Any]) -> User:
        """Update an existing user.

        Args:
            user_id (str): ID of the user to update.
            requester_id (str): ID of the user requesting the update.
            update_data (Dict[str, Any]): Data to update in the user (e.g., first_name, last_name).

        Returns:
            User: The updated user object.

        Raises:
            ValidationError: If user_id, requester_id, or data is invalid.
            NotFoundError: If user is not found.
            UnauthorizedError: If requester is not authorized.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(user_id, "user_id")
            validate_object_id(requester_id, "requester_id")
            user_update = UserUpdate(**update_data)  # اعتبارسنجی با Pydantic
            update_data_validated = user_update.model_dump(exclude_unset=True)

            user = cls.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")

            if requester_id != user_id:
                requester = cls.db.users.find_one({"_id": ObjectId(requester_id)})
                if not requester or "admin" not in requester.get("roles", []):
                    raise UnauthorizedError("You can only update your own profile unless you are an admin")

            update_data_validated["updated_at"] = datetime.now(timezone.utc)
            updated = cls.db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data_validated})
            if updated.matched_count == 0:
                raise InternalServerError(f"Failed to update user {user_id}")

            updated_user = cls.db.users.find_one({"_id": ObjectId(user_id)})
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

    def delete_user(cls, user_id: str, requester_id: str) -> Dict[str, str]:
        """Delete a user.

        Args:
            user_id (str): ID of the user to delete.
            requester_id (str): ID of the user requesting the deletion.

        Returns:
            Dict[str, str]: Confirmation message of deletion.

        Raises:
            ValidationError: If user_id or requester_id is invalid.
            NotFoundError: If user is not found.
            UnauthorizedError: If requester is not authorized.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(user_id, "user_id")
            validate_object_id(requester_id, "requester_id")

            user = cls.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")

            if requester_id != user_id:
                requester = cls.db.users.find_one({"_id": ObjectId(requester_id)})
                if not requester or "admin" not in requester.get("roles", []):
                    raise UnauthorizedError("You can only delete your own account unless you are an admin")

            cls.db.users.delete_one({"_id": ObjectId(user_id)})
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

    def get_all_users(self) -> List[User]:
        """Get all users (admin only)."""
        try:
            users = list(self.db.users.find())
            if not users:
                logger.debug("No users found in the database")
                return []
            logger.info(f"Retrieved {len(users)} users")
            return [User(**user) for user in users]
        except OperationFailure as of:
            logger.error(f"Database operation failed in get_all_users: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to get all users: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in get_all_users: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to get all users: {str(e)}")
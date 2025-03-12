# services/blocked_users.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.block import Block
from domain.schemas.block import BlockCreate
from domain.schemas.notification import NotificationCreate

logger = logging.getLogger(__name__)

from pydantic import BaseModel, field_validator


class BlockUpdate(BaseModel):
    reason: str | None = None

    @field_validator("reason")
    def validate_reason(cls, value):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Reason must be a non-empty string if provided")
        return value

def create_block(db: Database, blocker_id: str, block_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new block entry for a user or vendor with transaction for atomicity.

    Args:
        db (Database): MongoDB database instance.
        blocker_id (str): ID of the user or vendor initiating the block.
        block_data (Dict[str, Any]): Data for the block including blocked_id and optional reason.

    Returns:
        Dict[str, str]: Dictionary containing the created block ID.

    Raises:
        ValidationError: If input data is invalid.
        NotFoundError: If the blocked entity is not found.
        InternalServerError: For unexpected errors.
    """
    try:
        validate_object_id(blocker_id, "blocker_id")
        block_create = BlockCreate(**block_data)
        block_data_validated = block_create.model_dump()

        validate_object_id(block_data_validated["blocked_id"], "blocked_id")
        if blocker_id == block_data_validated["blocked_id"]:
            raise ValidationError("You cannot block yourcls")

        blocked_user = db.users.find_one({"_id": ObjectId(block_data_validated["blocked_id"])})
        blocked_vendor = db.vendors.find_one({"_id": ObjectId(block_data_validated["blocked_id"])})
        if not blocked_user and not blocked_vendor:
            raise NotFoundError(f"Blocked entity with ID {block_data_validated['blocked_id']} not found")

        block_data_validated["blocker_id"] = blocker_id
        block = Block(**block_data_validated)

        with db.client.start_session() as session:
            with session.start_transaction():
                # بررسی اتمی برای جلوگیری از بلاک تکراری
                existing_block = db.blocks.find_one({"blocker_id": blocker_id, "blocked_id": block_data_validated["blocked_id"]}, session=session)
                if existing_block:
                    raise ValidationError("This entity is already blocked")

                result = db.blocks.insert_one(block.model_dump(exclude={"id"}), session=session)
                block_id = str(result.inserted_id)

                # ایجاد اعلان برای کاربر یا فروشنده بلاک‌شده (فرضی)
                notification = NotificationCreate(
                    user_id=block_data_validated["blocked_id"] if blocked_user else None,
                    vendor_id=block_data_validated["blocked_id"] if blocked_vendor else None,
                    type="block",
                    message=f"You have been blocked by user/vendor {blocker_id}",
                    related_id=block_id
                ).model_dump()
                db.notifications.insert_one(notification, session=session)

        logger.info(f"Block created with ID: {block_id} by: {blocker_id}")
        return {"id": block_id}
    except (ValidationError, NotFoundError) as e:
        logger.error(f"Error in create_block: {e.detail}")
        raise e
    except DuplicateKeyError:
        logger.error("Duplicate block detected")
        raise ValidationError("This block already exists")
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_block: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create block: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_block: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create block: {str(e)}")

def get_block(db: Database, block_id: str, blocker_id: str) -> Block:
    """Retrieve a block by its ID.

    Args:
        db (Database): MongoDB database instance.
        block_id (str): ID of the block to retrieve.
        blocker_id (str): ID of the user or vendor requesting the block.

    Returns:
        Block: The requested block object.

    Raises:
        ValidationError: If block_id or blocker_id is invalid.
        NotFoundError: If block is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors.
    """
    try:
        validate_object_id(block_id, "block_id")
        validate_object_id(blocker_id, "blocker_id")

        block = db.blocks.find_one({"_id": ObjectId(block_id)})
        if not block:
            raise NotFoundError(f"Block with ID {block_id} not found")
        if block["blocker_id"] != blocker_id:
            raise UnauthorizedError("You can only view your own blocks")

        logger.info(f"Block retrieved: {block_id}")
        return Block(**block)
    except (ValidationError, NotFoundError, UnauthorizedError) as e:
        logger.error(f"Error in get_block: {e.detail}")
        raise e
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_block: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get block: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_block: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get block: {str(e)}")

def get_blocked_users(db: Database, blocker_id: str) -> List[Block]:
    """Retrieve all blocks created by a specific blocker.

    Args:
        db (Database): MongoDB database instance.
        blocker_id (str): ID of the user or vendor requesting their blocks.

    Returns:
        List[Block]: List of block objects.

    Raises:
        ValidationError: If blocker_id is invalid.
        InternalServerError: For unexpected errors.
    """
    try:
        validate_object_id(blocker_id, "blocker_id")

        blocks = list(db.blocks.find({"blocker_id": blocker_id}))
        if not blocks:
            logger.debug(f"No blocks found for blocker_id: {blocker_id}")
            return []

        logger.info(f"Retrieved {len(blocks)} blocks for blocker: {blocker_id}")
        return [Block(**block) for block in blocks]
    except ValidationError as ve:
        logger.error(f"Validation error in get_blocked_users: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_blocked_users: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get blocked users: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_blocked_users: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get blocked users: {str(e)}")

def update_block(db: Database, block_id: str, blocker_id: str, update_data: Dict[str, Any]) -> Block:
    """Update an existing block with validated data.

    Args:
        db (Database): MongoDB database instance.
        block_id (str): ID of the block to update.
        blocker_id (str): ID of the user or vendor updating the block.
        update_data (Dict[str, Any]): Data to update in the block (e.g., reason).

    Returns:
        Block: The updated block object.

    Raises:
        ValidationError: If block_id, blocker_id, or update data is invalid.
        NotFoundError: If block is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors.
    """
    try:
        validate_object_id(block_id, "block_id")
        validate_object_id(blocker_id, "blocker_id")
        block_update = BlockUpdate(**update_data)  # اعتبارسنجی با Pydantic
        update_data_validated = block_update.model_dump(exclude_unset=True)

        block = db.blocks.find_one({"_id": ObjectId(block_id)})
        if not block:
            raise NotFoundError(f"Block with ID {block_id} not found")
        if block["blocker_id"] != blocker_id:
            raise UnauthorizedError("You can only update your own blocks")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)
        updated = db.blocks.update_one({"_id": ObjectId(block_id)}, {"$set": update_data_validated})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update block {block_id}")

        updated_block = db.blocks.find_one({"_id": ObjectId(block_id)})
        logger.info(f"Block updated: {block_id}")
        return Block(**updated_block)
    except (ValidationError, NotFoundError, UnauthorizedError) as e:
        logger.error(f"Error in update_block: {e.detail}")
        raise e
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_block: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update block: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_block: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update block: {str(e)}")

def delete_block(db: Database, block_id: str, blocker_id: str) -> Dict[str, str]:
    """Delete a block with transaction for atomicity.

    Args:
        db (Database): MongoDB database instance.
        block_id (str): ID of the block to delete.
        blocker_id (str): ID of the user or vendor deleting the block.

    Returns:
        Dict[str, str]: Confirmation message of deletion.

    Raises:
        ValidationError: If block_id or blocker_id is invalid.
        NotFoundError: If block is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors.
    """
    try:
        validate_object_id(block_id, "block_id")
        validate_object_id(blocker_id, "blocker_id")

        block = db.blocks.find_one({"_id": ObjectId(block_id)})
        if not block:
            raise NotFoundError(f"Block with ID {block_id} not found")
        if block["blocker_id"] != blocker_id:
            raise UnauthorizedError("You can only delete your own blocks")

        with db.client.start_session() as session:
            with session.start_transaction():
                db.blocks.delete_one({"_id": ObjectId(block_id)}, session=session)
                # حذف اعلان مرتبط (فرضی)
                db.notifications.delete_one({"related_id": block_id, "type": "block"}, session=session)

        logger.info(f"Block deleted: {block_id}")
        return {"message": f"Block {block_id} deleted successfully"}
    except (ValidationError, NotFoundError, UnauthorizedError) as e:
        logger.error(f"Error in delete_block: {e.detail}")
        raise e
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_block: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete block: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_block: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete block: {str(e)}")
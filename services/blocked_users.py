# services/blocked_users.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from domain.entities.block import Block

logger = logging.getLogger(__name__)


def create_block(db: Database, blocker_id: str, block_data: dict) -> dict:
    """Create a new block entry for a user or vendor.

    Args:
        db (Database): MongoDB database instance.
        blocker_id (str): ID of the user or vendor initiating the block.
        block_data (dict): Data for the block including blocked_id and reason.

    Returns:
        dict: Dictionary containing the created block ID.

    Raises:
        ValidationError: If input data is invalid.
        NotFoundError: If the blocked entity is not found.
        InternalServerError: For unexpected errors.
    """
    try:
        if not ObjectId.is_valid(blocker_id):
            raise ValidationError(f"Invalid blocker_id format: {blocker_id}")
        if not block_data.get("blocked_id"):
            raise ValidationError("Blocked ID is required")
        if not ObjectId.is_valid(block_data["blocked_id"]):
            raise ValidationError(f"Invalid blocked_id format: {block_data['blocked_id']}")
        if blocker_id == block_data["blocked_id"]:
            raise ValidationError("You cannot block yourself")

        # بررسی وجود کاربر یا وندور بلاک‌شده
        blocked_user = db.users.find_one({"_id": ObjectId(block_data["blocked_id"])})
        blocked_vendor = db.vendors.find_one({"_id": ObjectId(block_data["blocked_id"])})
        if not blocked_user and not blocked_vendor:
            raise NotFoundError(f"Blocked entity with ID {block_data['blocked_id']} not found")

        # بررسی اینکه آیا قبلاً بلاک شده یا نه
        existing_block = db.blocks.find_one({"blocker_id": blocker_id, "blocked_id": block_data["blocked_id"]})
        if existing_block:
            raise ValidationError("This entity is already blocked")

        block_data["blocker_id"] = blocker_id
        block = Block(**block_data)
        result = db.blocks.insert_one(block.model_dump(exclude={"id"}))
        block_id = str(result.inserted_id)
        logger.info(f"Block created with ID: {block_id} by: {blocker_id}")
        return {"id": block_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_block: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_block: {ne.detail}")
        raise ne
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
        if not ObjectId.is_valid(block_id):
            raise ValidationError(f"Invalid block ID format: {block_id}")
        if not ObjectId.is_valid(blocker_id):
            raise ValidationError(f"Invalid blocker_id format: {blocker_id}")

        block = db.blocks.find_one({"_id": ObjectId(block_id)})
        if not block:
            raise NotFoundError(f"Block with ID {block_id} not found")
        if block["blocker_id"] != blocker_id:
            raise UnauthorizedError("You can only view your own blocks")

        logger.info(f"Block retrieved: {block_id}")
        return Block(**block)
    except ValidationError as ve:
        logger.error(f"Validation error in get_block: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_block: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_block: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_block: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get block: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_block: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get block: {str(e)}")


def get_blocked_users(db: Database, blocker_id: str) -> list[Block]:
    """Retrieve all blocks created by a specific blocker.

    Args:
        db (Database): MongoDB database instance.
        blocker_id (str): ID of the user or vendor requesting their blocks.

    Returns:
        list[Block]: List of block objects.

    Raises:
        ValidationError: If blocker_id is invalid.
        InternalServerError: For unexpected errors.
    """
    try:
        if not ObjectId.is_valid(blocker_id):
            raise ValidationError(f"Invalid blocker_id format: {blocker_id}")

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


def update_block(db: Database, block_id: str, blocker_id: str, update_data: dict) -> Block:
    """Update an existing block.

    Args:
        db (Database): MongoDB database instance.
        block_id (str): ID of the block to update.
        blocker_id (str): ID of the user or vendor updating the block.
        update_data (dict): Data to update in the block.

    Returns:
        Block: The updated block object.

    Raises:
        ValidationError: If block_id or blocker_id is invalid.
        NotFoundError: If block is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors.
    """
    try:
        if not ObjectId.is_valid(block_id):
            raise ValidationError(f"Invalid block ID format: {block_id}")
        if not ObjectId.is_valid(blocker_id):
            raise ValidationError(f"Invalid blocker_id format: {blocker_id}")

        block = db.blocks.find_one({"_id": ObjectId(block_id)})
        if not block:
            raise NotFoundError(f"Block with ID {block_id} not found")
        if block["blocker_id"] != blocker_id:
            raise UnauthorizedError("You can only update your own blocks")

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = db.blocks.update_one({"_id": ObjectId(block_id)}, {"$set": update_data})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update block {block_id}")

        updated_block = db.blocks.find_one({"_id": ObjectId(block_id)})
        logger.info(f"Block updated: {block_id}")
        return Block(**updated_block)
    except ValidationError as ve:
        logger.error(f"Validation error in update_block: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_block: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_block: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_block: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update block: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_block: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update block: {str(e)}")


def delete_block(db: Database, block_id: str, blocker_id: str) -> dict:
    """Delete a block.

    Args:
        db (Database): MongoDB database instance.
        block_id (str): ID of the block to delete.
        blocker_id (str): ID of the user or vendor deleting the block.

    Returns:
        dict: Confirmation message of deletion.

    Raises:
        ValidationError: If block_id or blocker_id is invalid.
        NotFoundError: If block is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors.
    """
    try:
        if not ObjectId.is_valid(block_id):
            raise ValidationError(f"Invalid block ID format: {block_id}")
        if not ObjectId.is_valid(blocker_id):
            raise ValidationError(f"Invalid blocker_id format: {blocker_id}")

        block = db.blocks.find_one({"_id": ObjectId(block_id)})
        if not block:
            raise NotFoundError(f"Block with ID {block_id} not found")
        if block["blocker_id"] != blocker_id:
            raise UnauthorizedError("You can only delete your own blocks")

        db.blocks.delete_one({"_id": ObjectId(block_id)})
        logger.info(f"Block deleted: {block_id}")
        return {"message": f"Block {block_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_block: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_block: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_block: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_block: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete block: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_block: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete block: {str(e)}")

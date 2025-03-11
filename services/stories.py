# services/stories.py
import logging
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from domain.entities.story import Story

logger = logging.getLogger(__name__)


def create_story(db: Database, vendor_id: str, story_data: dict) -> dict:
    """Create a new story for a vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor creating the story.
        story_data (dict): Data for the story including media_type and media_url.

    Returns:
        dict: Dictionary containing the created story ID.

    Raises:
        ValidationError: If required fields are missing or invalid.
        NotFoundError: If vendor is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")
        if not story_data.get("media_type") or not story_data.get("media_url"):
            raise ValidationError("Media type and URL are required")
        if story_data["media_type"] not in ["image", "video"]:
            raise ValidationError("Media type must be 'image' or 'video'")

        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")

        if not story_data.get("expires_at"):
            story_data["expires_at"] = datetime.now(timezone.utc) + timedelta(hours=24)

        story_data["vendor_id"] = vendor_id
        story = Story(**story_data)
        result = db.stories.insert_one(story.model_dump(exclude={"id"}))
        story_id = str(result.inserted_id)

        db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$push": {"stories": story_id}})
        logger.info(f"Story created with ID: {story_id} for vendor: {vendor_id}")
        return {"id": story_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_story: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_story: {ne.detail}")
        raise ne
    except DuplicateKeyError:
        logger.error("Duplicate story detected")
        raise ValidationError("A story with this data already exists")
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_story: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create story: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_story: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create story: {str(e)}")


def get_story(db: Database, story_id: str) -> Story:
    """Retrieve a story by its ID.

    Args:
        db (Database): MongoDB database instance.
        story_id (str): ID of the story to retrieve.

    Returns:
        Story: The requested story object.

    Raises:
        ValidationError: If story_id format is invalid.
        NotFoundError: If story is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(story_id):
            raise ValidationError(f"Invalid story ID format: {story_id}")

        story = db.stories.find_one({"_id": ObjectId(story_id)})
        if not story:
            raise NotFoundError(f"Story with ID {story_id} not found")

        # بررسی انقضا
        now = datetime.now(timezone.utc)
        if story["expires_at"] < now and story["status"] != "expired":
            db.stories.update_one({"_id": ObjectId(story_id)}, {"$set": {"status": "expired", "updated_at": now}})
            story["status"] = "expired"
            logger.debug(f"Story {story_id} marked as expired")

        logger.info(f"Story retrieved: {story_id}")
        return Story(**story)
    except ValidationError as ve:
        logger.error(f"Validation error in get_story: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_story: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_story: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get story: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_story: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get story: {str(e)}")


def get_stories_by_vendor(db: Database, vendor_id: str) -> list[Story]:
    """Retrieve all stories for a specific vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve stories for.

    Returns:
        list[Story]: List of story objects.

    Raises:
        ValidationError: If vendor_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        stories = list(db.stories.find({"vendor_id": vendor_id}))
        if not stories:
            logger.debug(f"No stories found for vendor_id: {vendor_id}")
            return []

        now = datetime.now(timezone.utc)
        for story in stories:
            if story["expires_at"] < now and story["status"] != "expired":
                db.stories.update_one({"_id": story["_id"]}, {"$set": {"status": "expired", "updated_at": now}})
                story["status"] = "expired"
                logger.debug(f"Story {story['_id']} marked as expired during retrieval")

        logger.info(f"Retrieved {len(stories)} stories for vendor_id: {vendor_id}")
        return [Story(**story) for story in stories]
    except ValidationError as ve:
        logger.error(f"Validation error in get_stories_by_vendor: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_stories_by_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get stories: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_stories_by_vendor: {str(e)}, vendor_id: {vendor_id}", exc_info=True)
        raise InternalServerError(f"Failed to get stories: {str(e)}")


def get_all_stories(db: Database) -> list[Story]:
    """Retrieve all active stories.

    Args:
        db (Database): MongoDB database instance.

    Returns:
        list[Story]: List of all active story objects.

    Raises:
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        now = datetime.now(timezone.utc)
        stories = list(db.stories.find({"status": "active", "expires_at": {"$gte": now}}))
        if not stories:
            logger.debug("No active stories found")
            return []

        logger.info(f"Retrieved {len(stories)} active stories")
        return [Story(**story) for story in stories]
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_all_stories: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get all stories: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_all_stories: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get all stories: {str(e)}")


def update_story(db: Database, story_id: str, vendor_id: str, update_data: dict) -> Story:
    """Update an existing story.

    Args:
        db (Database): MongoDB database instance.
        story_id (str): ID of the story to update.
        vendor_id (str): ID of the vendor updating the story.
        update_data (dict): Data to update in the story.

    Returns:
        Story: The updated story object.

    Raises:
        ValidationError: If story_id or vendor_id is invalid.
        NotFoundError: If story is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(story_id):
            raise ValidationError(f"Invalid story ID format: {story_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        story = db.stories.find_one({"_id": ObjectId(story_id)})
        if not story:
            raise NotFoundError(f"Story with ID {story_id} not found")
        if story["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only update your own stories")

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = db.stories.update_one({"_id": ObjectId(story_id)}, {"$set": update_data})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update story {story_id}")

        updated_story = db.stories.find_one({"_id": ObjectId(story_id)})
        logger.info(f"Story updated: {story_id}")
        return Story(**updated_story)
    except ValidationError as ve:
        logger.error(f"Validation error in update_story: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_story: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_story: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_story: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update story: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_story: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update story: {str(e)}")


def delete_story(db: Database, story_id: str, vendor_id: str) -> dict:
    """Delete a story.

    Args:
        db (Database): MongoDB database instance.
        story_id (str): ID of the story to delete.
        vendor_id (str): ID of the vendor deleting the story.

    Returns:
        dict: Confirmation message of deletion.

    Raises:
        ValidationError: If story_id or vendor_id is invalid.
        NotFoundError: If story is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(story_id):
            raise ValidationError(f"Invalid story ID format: {story_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        story = db.stories.find_one({"_id": ObjectId(story_id)})
        if not story:
            raise NotFoundError(f"Story with ID {story_id} not found")
        if story["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only delete your own stories")

        db.stories.delete_one({"_id": ObjectId(story_id)})
        db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$pull": {"stories": story_id}})
        logger.info(f"Story deleted: {story_id}")
        return {"message": f"Story {story_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_story: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_story: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_story: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_story: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete story: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_story: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete story: {str(e)}")

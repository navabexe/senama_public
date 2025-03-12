# services/stories.py
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.story import Story
from domain.schemas.story import StoryCreate, StoryUpdate

logger = logging.getLogger(__name__)

def create_story(db: Database, vendor_id: str, story_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new story for a vendor with atomic check to prevent duplicates.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor creating the story.
        story_data (Dict[str, Any]): Data for the story including media_type and media_url.

    Returns:
        Dict[str, str]: Dictionary containing the created story ID.

    Raises:
        ValidationError: If required fields are missing, invalid, or story already exists.
        NotFoundError: If vendor is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(vendor_id, "vendor_id")
        story_create = StoryCreate(**story_data)  # اعتبارسنجی با Pydantic
        story_data_validated = story_create.model_dump()

        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")

        if "expires_at" not in story_data_validated:
            story_data_validated["expires_at"] = datetime.now(timezone.utc) + timedelta(hours=24)

        story_data_validated["vendor_id"] = vendor_id
        story = Story(**story_data_validated)

        with db.client.start_session() as session:
            with session.start_transaction():
                # بررسی اتمی برای جلوگیری از استوری تکراری
                query = {
                    "vendor_id": vendor_id,
                    "media_url": story_data_validated["media_url"]
                }
                existing_story = db.stories.find_one(query, session=session)
                if existing_story:
                    raise ValidationError(f"A story with this media URL already exists for vendor {vendor_id}")

                result = db.stories.insert_one(story.model_dump(exclude={"id"}), session=session)
                story_id = str(result.inserted_id)
                db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$push": {"stories": story_id}}, session=session)

        logger.info(f"Story created with ID: {story_id} for vendor: {vendor_id}")
        return {"id": story_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_story: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_story: {ne.detail}")
        raise ne
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
        validate_object_id(story_id, "story_id")

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

def get_stories_by_vendor(db: Database, vendor_id: str) -> List[Story]:
    """Retrieve all stories for a specific vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve stories for.

    Returns:
        List[Story]: List of story objects.

    Raises:
        ValidationError: If vendor_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(vendor_id, "vendor_id")

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

def get_all_stories(db: Database) -> List[Story]:
    """Retrieve all active stories.

    Args:
        db (Database): MongoDB database instance.

    Returns:
        List[Story]: List of all active story objects.

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

def update_story(db: Database, story_id: str, vendor_id: str, update_data: Dict[str, Any]) -> Story:
    """Update an existing story.

    Args:
        db (Database): MongoDB database instance.
        story_id (str): ID of the story to update.
        vendor_id (str): ID of the vendor updating the story.
        update_data (Dict[str, Any]): Data to update in the story (e.g., media_url, expires_at).

    Returns:
        Story: The updated story object.

    Raises:
        ValidationError: If story_id, vendor_id, or fields are invalid.
        NotFoundError: If story is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(story_id, "story_id")
        validate_object_id(vendor_id, "vendor_id")
        story_update = StoryUpdate(**update_data)  # اعتبارسنجی با Pydantic
        update_data_validated = story_update.model_dump(exclude_unset=True)

        story = db.stories.find_one({"_id": ObjectId(story_id)})
        if not story:
            raise NotFoundError(f"Story with ID {story_id} not found")
        if story["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only update your own stories")

        if "media_type" in update_data_validated and update_data_validated["media_type"] not in ["image", "video"]:
            raise ValidationError("Media type must be 'image' or 'video'")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)
        updated = db.stories.update_one({"_id": ObjectId(story_id)}, {"$set": update_data_validated})
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

def delete_story(db: Database, story_id: str, vendor_id: str) -> Dict[str, str]:
    """Delete a story with transaction to update vendor's story list.

    Args:
        db (Database): MongoDB database instance.
        story_id (str): ID of the story to delete.
        vendor_id (str): ID of the vendor deleting the story.

    Returns:
        Dict[str, str]: Confirmation message of deletion.

    Raises:
        ValidationError: If story_id or vendor_id is invalid.
        NotFoundError: If story is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(story_id, "story_id")
        validate_object_id(vendor_id, "vendor_id")

        story = db.stories.find_one({"_id": ObjectId(story_id)})
        if not story:
            raise NotFoundError(f"Story with ID {story_id} not found")
        if story["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only delete your own stories")

        with db.client.start_session() as session:
            with session.start_transaction():
                db.stories.delete_one({"_id": ObjectId(story_id)}, session=session)
                db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$pull": {"stories": story_id}}, session=session)

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
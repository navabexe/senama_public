# services/business_categories.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, InternalServerError
from domain.entities.business_category import BusinessCategory

logger = logging.getLogger(__name__)


def create_business_category(db: Database, category_data: dict) -> dict:
    """Create a new business category.

    Args:
        db (Database): MongoDB database instance.
        category_data (dict): Data for the business category including name and description.

    Returns:
        dict: Dictionary containing the created category ID.

    Raises:
        ValidationError: If category name is missing or already exists.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not category_data.get("name"):
            raise ValidationError("Category name is required")
        if db.business_categories.find_one({"name": category_data["name"]}):
            raise ValidationError("Category name already exists")

        category = BusinessCategory(**category_data)
        result = db.business_categories.insert_one(category.model_dump(exclude={"id"}))
        category_id = str(result.inserted_id)
        logger.info(f"Business category created with ID: {category_id}")
        return {"id": category_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_business_category: {ve.detail}")
        raise ve
    except DuplicateKeyError:
        logger.error("Duplicate business category detected")
        raise ValidationError("A business category with this name already exists")
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_business_category: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create business category: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_business_category: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create business category: {str(e)}")


def get_business_category(db: Database, category_id: str) -> BusinessCategory:
    """Retrieve a business category by its ID.

    Args:
        db (Database): MongoDB database instance.
        category_id (str): ID of the business category to retrieve.

    Returns:
        BusinessCategory: The requested business category object.

    Raises:
        ValidationError: If category_id format is invalid.
        NotFoundError: If category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(category_id):
            raise ValidationError(f"Invalid category ID format: {category_id}")

        category = db.business_categories.find_one({"_id": ObjectId(category_id)})
        if not category:
            raise NotFoundError(f"Business category with ID {category_id} not found")

        logger.info(f"Business category retrieved: {category_id}")
        return BusinessCategory(**category)
    except ValidationError as ve:
        logger.error(f"Validation error in get_business_category: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_business_category: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_business_category: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get business category: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_business_category: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get business category: {str(e)}")


def get_all_business_categories(db: Database) -> list[BusinessCategory]:
    """Retrieve all business categories.

    Args:
        db (Database): MongoDB database instance.

    Returns:
        list[BusinessCategory]: List of all business category objects.

    Raises:
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        categories = list(db.business_categories.find())
        if not categories:
            logger.debug("No business categories found in the database")
            return []

        logger.info(f"Retrieved {len(categories)} business categories")
        return [BusinessCategory(**category) for category in categories]
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_all_business_categories: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get all business categories: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_all_business_categories: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get all business categories: {str(e)}")


def update_business_category(db: Database, category_id: str, update_data: dict) -> BusinessCategory:
    """Update an existing business category.

    Args:
        db (Database): MongoDB database instance.
        category_id (str): ID of the business category to update.
        update_data (dict): Data to update in the business category.

    Returns:
        BusinessCategory: The updated business category object.

    Raises:
        ValidationError: If category_id or status is invalid.
        NotFoundError: If category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(category_id):
            raise ValidationError(f"Invalid category ID format: {category_id}")

        category = db.business_categories.find_one({"_id": ObjectId(category_id)})
        if not category:
            raise NotFoundError(f"Business category with ID {category_id} not found")

        update_data["updated_at"] = datetime.now(timezone.utc)
        if "status" in update_data and update_data["status"] not in ["active", "inactive"]:
            raise ValidationError("Invalid status value")

        updated = db.business_categories.update_one({"_id": ObjectId(category_id)}, {"$set": update_data})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update business category {category_id}")

        updated_category = db.business_categories.find_one({"_id": ObjectId(category_id)})
        logger.info(f"Business category updated: {category_id}")
        return BusinessCategory(**updated_category)
    except ValidationError as ve:
        logger.error(f"Validation error in update_business_category: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_business_category: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_business_category: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update business category: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_business_category: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update business category: {str(e)}")


def delete_business_category(db: Database, category_id: str) -> dict:
    """Delete a business category.

    Args:
        db (Database): MongoDB database instance.
        category_id (str): ID of the business category to delete.

    Returns:
        dict: Confirmation message of deletion.

    Raises:
        ValidationError: If category_id format is invalid.
        NotFoundError: If category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(category_id):
            raise ValidationError(f"Invalid category ID format: {category_id}")

        category = db.business_categories.find_one({"_id": ObjectId(category_id)})
        if not category:
            raise NotFoundError(f"Business category with ID {category_id} not found")

        db.business_categories.delete_one({"_id": ObjectId(category_id)})
        logger.info(f"Business category deleted: {category_id}")
        return {"message": f"Business category {category_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_business_category: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_business_category: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_business_category: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete business category: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_business_category: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete business category: {str(e)}")

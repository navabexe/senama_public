# services/product_categories.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.product_category import ProductCategory
from domain.schemas.product_category import ProductCategoryCreate, ProductCategoryUpdate

logger = logging.getLogger(__name__)

def create_product_category(db: Database, category_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new product category with atomic check to prevent duplicates.

    Args:
        db (Database): MongoDB database instance.
        category_data (Dict[str, Any]): Data for the product category including name and optional description.

    Returns:
        Dict[str, str]: Dictionary containing the created category ID.

    Raises:
        ValidationError: If category name is missing, invalid, or already exists.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        category_create = ProductCategoryCreate(**category_data)  # اعتبارسنجی با Pydantic
        category_data_validated = category_create.model_dump()

        with db.client.start_session() as session:
            with session.start_transaction():
                # بررسی اتمی برای جلوگیری از دسته‌بندی تکراری
                if db.product_categories.find_one({"name": category_data_validated["name"]}, session=session):
                    raise ValidationError("Category name already exists")

                category = ProductCategory(**category_data_validated)
                result = db.product_categories.insert_one(category.model_dump(exclude={"id"}), session=session)
                category_id = str(result.inserted_id)

        logger.info(f"Product category created with ID: {category_id}")
        return {"id": category_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_product_category: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_product_category: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create product category: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_product_category: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create product category: {str(e)}")

def get_product_category(db: Database, category_id: str) -> ProductCategory:
    """Retrieve a product category by its ID.

    Args:
        db (Database): MongoDB database instance.
        category_id (str): ID of the product category to retrieve.

    Returns:
        ProductCategory: The requested product category object.

    Raises:
        ValidationError: If category_id format is invalid.
        NotFoundError: If category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(category_id, "category_id")

        category = db.product_categories.find_one({"_id": ObjectId(category_id)})
        if not category:
            raise NotFoundError(f"Product category with ID {category_id} not found")

        logger.info(f"Product category retrieved: {category_id}")
        return ProductCategory(**category)
    except ValidationError as ve:
        logger.error(f"Validation error in get_product_category: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_product_category: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_product_category: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get product category: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_product_category: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get product category: {str(e)}")

def get_all_product_categories(db: Database) -> List[ProductCategory]:
    """Retrieve all product categories.

    Args:
        db (Database): MongoDB database instance.

    Returns:
        List[ProductCategory]: List of all product category objects.

    Raises:
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        categories = list(db.product_categories.find())
        if not categories:
            logger.debug("No product categories found in the database")
            return []

        logger.info(f"Retrieved {len(categories)} product categories")
        return [ProductCategory(**category) for category in categories]
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_all_product_categories: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get all product categories: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_all_product_categories: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get all product categories: {str(e)}")

def update_product_category(db: Database, category_id: str, update_data: Dict[str, Any]) -> ProductCategory:
    """Update an existing product category.

    Args:
        db (Database): MongoDB database instance.
        category_id (str): ID of the product category to update.
        update_data (Dict[str, Any]): Data to update in the product category (e.g., name, description, status).

    Returns:
        ProductCategory: The updated product category object.

    Raises:
        ValidationError: If category_id or update data is invalid.
        NotFoundError: If category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(category_id, "category_id")
        category_update = ProductCategoryUpdate(**update_data)  # اعتبارسنجی با Pydantic
        update_data_validated = category_update.model_dump(exclude_unset=True)

        category = db.product_categories.find_one({"_id": ObjectId(category_id)})
        if not category:
            raise NotFoundError(f"Product category with ID {category_id} not found")

        if "name" in update_data_validated and update_data_validated["name"] != category["name"]:
            if db.product_categories.find_one({"name": update_data_validated["name"]}):
                raise ValidationError("Category name already exists")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)
        updated = db.product_categories.update_one({"_id": ObjectId(category_id)}, {"$set": update_data_validated})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update product category {category_id}")

        updated_category = db.product_categories.find_one({"_id": ObjectId(category_id)})
        logger.info(f"Product category updated: {category_id}")
        return ProductCategory(**updated_category)
    except ValidationError as ve:
        logger.error(f"Validation error in update_product_category: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_product_category: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_product_category: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update product category: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_product_category: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update product category: {str(e)}")

def delete_product_category(db: Database, category_id: str) -> Dict[str, str]:
    """Delete a product category with transaction if related products exist.

    Args:
        db (Database): MongoDB database instance.
        category_id (str): ID of the product category to delete.

    Returns:
        Dict[str, str]: Confirmation message of deletion.

    Raises:
        ValidationError: If category_id is invalid.
        NotFoundError: If category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(category_id, "category_id")

        category = db.product_categories.find_one({"_id": ObjectId(category_id)})
        if not category:
            raise NotFoundError(f"Product category with ID {category_id} not found")

        # بررسی وجود محصولات مرتبط
        products_using_category = db.products.find_one({"category_id": category_id})
        if products_using_category:
            with db.client.start_session() as session:
                with session.start_transaction():
                    # حذف دسته‌بندی از محصولات
                    db.products.update_many(
                        {"category_id": category_id},
                        {"$unset": {"category_id": ""}},
                        session=session
                    )
                    db.product_categories.delete_one({"_id": ObjectId(category_id)}, session=session)
        else:
            db.product_categories.delete_one({"_id": ObjectId(category_id)})

        logger.info(f"Product category deleted: {category_id}")
        return {"message": f"Product category {category_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_product_category: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_product_category: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_product_category: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete product category: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_product_category: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete product category: {str(e)}")
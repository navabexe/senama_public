# services/products.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.product import Product
from domain.schemas.product import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)

def create_product(db: Database, vendor_id: str, product_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new product for a vendor with atomic check to prevent duplicates.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor creating the product.
        product_data (Dict[str, Any]): Data for the product including name, price, quantity, and category_id.

    Returns:
        Dict[str, str]: Dictionary containing the created product ID.

    Raises:
        ValidationError: If required fields are missing, invalid, or product already exists.
        NotFoundError: If vendor or category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Attempting to create product for vendor_id: {vendor_id} with data: {product_data}")
    try:
        validate_object_id(vendor_id, "vendor_id")
        product_create = ProductCreate(**product_data)  # اعتبارسنجی با Pydantic
        product_data_validated = product_create.model_dump()

        validate_object_id(product_data_validated["category_id"], "category_id")

        if not db.product_categories.find_one({"_id": ObjectId(product_data_validated["category_id"])}):
            raise ValidationError(f"Product category {product_data_validated['category_id']} not found")

        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")

        product_data_validated["vendor_id"] = vendor_id
        product = Product(**product_data_validated)

        with db.client.start_session() as session:
            with session.start_transaction():
                # بررسی اتمی برای جلوگیری از محصول تکراری
                query = {
                    "vendor_id": vendor_id,
                    "name": product_data_validated["name"]
                }
                existing_product = db.products.find_one(query, session=session)
                if existing_product:
                    raise ValidationError(f"A product with name '{product_data_validated['name']}' already exists for this vendor")

                result = db.products.insert_one(product.model_dump(exclude={"id"}), session=session)
                product_id = str(result.inserted_id)
                db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$push": {"products": product_id}}, session=session)

        logger.info(f"Product created successfully - ID: {product_id}, vendor_id: {vendor_id}, data: {product_data_validated}")
        return {"id": product_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_product: {ve.detail}, input: {product_data}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_product: {ne.detail}, vendor_id: {vendor_id}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_product: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create product: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_product: {str(e)}, vendor_id: {vendor_id}, input: {product_data}", exc_info=True)
        raise InternalServerError(f"Failed to create product: {str(e)}")

def get_product(db: Database, product_id: str) -> Product:
    """Retrieve a product by its ID.

    Args:
        db (Database): MongoDB database instance.
        product_id (str): ID of the product to retrieve.

    Returns:
        Product: The requested product object.

    Raises:
        ValidationError: If product_id format is invalid.
        NotFoundError: If product is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Fetching product with ID: {product_id}")
    try:
        validate_object_id(product_id, "product_id")

        product = db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            logger.warning(f"Product with ID {product_id} not found")
            raise NotFoundError(f"Product with ID {product_id} not found")

        logger.info(f"Product retrieved successfully - ID: {product_id}")
        return Product(**product)
    except ValidationError as ve:
        logger.error(f"Validation error in get_product: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_product: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_product: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get product: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_product: {str(e)}, product_id: {product_id}", exc_info=True)
        raise InternalServerError(f"Failed to get product: {str(e)}")

def get_products_by_vendor(db: Database, vendor_id: str) -> List[Product]:
    """Retrieve all products for a specific vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve products for.

    Returns:
        List[Product]: List of product objects.

    Raises:
        ValidationError: If vendor_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Fetching products for vendor_id: {vendor_id}")
    try:
        validate_object_id(vendor_id, "vendor_id")

        products = list(db.products.find({"vendor_id": vendor_id}))
        if not products:
            logger.debug(f"No products found for vendor_id: {vendor_id}")
            return []

        logger.info(f"Retrieved {len(products)} products for vendor_id: {vendor_id}")
        return [Product(**product) for product in products]
    except ValidationError as ve:
        logger.error(f"Validation error in get_products_by_vendor: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_products_by_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get products: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_products_by_vendor: {str(e)}, vendor_id: {vendor_id}", exc_info=True)
        raise InternalServerError(f"Failed to get products: {str(e)}")

def get_all_products(db: Database) -> List[Product]:
    """Retrieve all products.

    Args:
        db (Database): MongoDB database instance.

    Returns:
        List[Product]: List of all product objects.

    Raises:
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug("Fetching all products")
    try:
        products = list(db.products.find())
        if not products:
            logger.debug("No products found in the database")
            return []

        logger.info(f"Retrieved {len(products)} products")
        return [Product(**product) for product in products]
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_all_products: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get all products: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_all_products: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get all products: {str(e)}")

def update_product(db: Database, product_id: str, vendor_id: str, update_data: Dict[str, Any]) -> Product:
    """Update an existing product.

    Args:
        db (Database): MongoDB database instance.
        product_id (str): ID of the product to update.
        vendor_id (str): ID of the vendor updating the product.
        update_data (Dict[str, Any]): Data to update in the product (e.g., name, price, quantity).

    Returns:
        Product: The updated product object.

    Raises:
        ValidationError: If product_id, vendor_id, or fields are invalid.
        NotFoundError: If product is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Updating product with ID: {product_id} for vendor_id: {vendor_id}, data: {update_data}")
    try:
        validate_object_id(product_id, "product_id")
        validate_object_id(vendor_id, "vendor_id")
        product_update = ProductUpdate(**update_data)  # اعتبارسنجی با Pydantic
        update_data_validated = product_update.model_dump(exclude_unset=True)

        product = db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            logger.warning(f"Product with ID {product_id} not found")
            raise NotFoundError(f"Product with ID {product_id} not found")
        if product["vendor_id"] != vendor_id:
            logger.warning(f"Unauthorized update attempt on product {product_id} by vendor {vendor_id}")
            raise UnauthorizedError("You can only update your own products")

        if "category_id" in update_data_validated:
            validate_object_id(update_data_validated["category_id"], "category_id")
            if not db.product_categories.find_one({"_id": ObjectId(update_data_validated["category_id"])}):
                raise ValidationError(f"Product category {update_data_validated['category_id']} not found")

        if "name" in update_data_validated and update_data_validated["name"] != product["name"]:
            if db.products.find_one({"vendor_id": vendor_id, "name": update_data_validated["name"]}):
                raise ValidationError(f"A product with name '{update_data_validated['name']}' already exists for this vendor")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)
        updated = db.products.update_one({"_id": ObjectId(product_id)}, {"$set": update_data_validated})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update product {product_id}")

        updated_product = db.products.find_one({"_id": ObjectId(product_id)})
        logger.info(f"Product updated successfully - ID: {product_id}, changes: {update_data_validated}")
        return Product(**updated_product)
    except ValidationError as ve:
        logger.error(f"Validation error in update_product: {ve.detail}, input: {update_data}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_product: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_product: {ue.detail}, vendor_id: {vendor_id}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_product: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update product: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_product: {str(e)}, product_id: {product_id}, input: {update_data}", exc_info=True)
        raise InternalServerError(f"Failed to update product: {str(e)}")

def delete_product(db: Database, product_id: str, vendor_id: str) -> Dict[str, str]:
    """Delete a product with transaction to update vendor's product list.

    Args:
        db (Database): MongoDB database instance.
        product_id (str): ID of the product to delete.
        vendor_id (str): ID of the vendor deleting the product.

    Returns:
        Dict[str, str]: Confirmation message of deletion.

    Raises:
        ValidationError: If product_id or vendor_id is invalid.
        NotFoundError: If product is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Deleting product with ID: {product_id} for vendor_id: {vendor_id}")
    try:
        validate_object_id(product_id, "product_id")
        validate_object_id(vendor_id, "vendor_id")

        product = db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            logger.warning(f"Product with ID {product_id} not found")
            raise NotFoundError(f"Product with ID {product_id} not found")
        if product["vendor_id"] != vendor_id:
            logger.warning(f"Unauthorized delete attempt on product {product_id} by vendor {vendor_id}")
            raise UnauthorizedError("You can only delete your own products")

        with db.client.start_session() as session:
            with session.start_transaction():
                db.products.delete_one({"_id": ObjectId(product_id)}, session=session)
                db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$pull": {"products": product_id}}, session=session)

        logger.info(f"Product deleted successfully - ID: {product_id} by vendor: {vendor_id}")
        return {"message": f"Product {product_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_product: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_product: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_product: {ue.detail}, vendor_id: {vendor_id}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_product: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete product: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_product: {str(e)}, product_id: {product_id}, vendor_id: {vendor_id}", exc_info=True)
        raise InternalServerError(f"Failed to delete product: {str(e)}")
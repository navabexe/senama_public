# services/products.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from domain.entities.product import Product

logger = logging.getLogger(__name__)


def create_product(db: Database, vendor_id: str, product_data: dict) -> dict:
    """Create a new product for a vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor creating the product.
        product_data (dict): Data for the product including name, price, quantity, and category_id.

    Returns:
        dict: Dictionary containing the created product ID.

    Raises:
        ValidationError: If required fields are missing or invalid.
        NotFoundError: If vendor or category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Attempting to create product for vendor_id: {vendor_id} with data: {product_data}")
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        required_fields = ["name", "price", "quantity", "category_id"]
        for field in required_fields:
            if field not in product_data or not product_data[field]:
                raise ValidationError(f"{field} is required")

        if not isinstance(product_data["price"], (int, float)) or product_data["price"] <= 0:
            raise ValidationError("Price must be a positive number")
        if not isinstance(product_data["quantity"], int) or product_data["quantity"] < 0:
            raise ValidationError("Quantity must be a non-negative integer")
        if not ObjectId.is_valid(product_data["category_id"]):
            raise ValidationError(f"Invalid category_id format: {product_data['category_id']}")

        if not db.product_categories.find_one({"_id": ObjectId(product_data["category_id"])}):
            raise ValidationError(f"Product category {product_data['category_id']} not found")

        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")

        product_data["vendor_id"] = vendor_id
        product = Product(**product_data)
        result = db.products.insert_one(product.model_dump(exclude={"id"}))
        product_id = str(result.inserted_id)

        db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$push": {"products": product_id}})
        logger.info(f"Product created successfully - ID: {product_id}, vendor_id: {vendor_id}, data: {product_data}")
        return {"id": product_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_product: {ve.detail}, input: {product_data}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_product: {ne.detail}, vendor_id: {vendor_id}")
        raise ne
    except DuplicateKeyError as dke:
        logger.error(f"Duplicate key error in create_product: {str(dke)}, input: {product_data}")
        raise ValidationError("A product with this name already exists for this vendor")
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_product: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create product: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_product: {str(e)}, vendor_id: {vendor_id}, input: {product_data}",
                     exc_info=True)
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
        if not ObjectId.is_valid(product_id):
            raise ValidationError(f"Invalid product ID format: {product_id}")

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


def get_products_by_vendor(db: Database, vendor_id: str) -> list[Product]:
    """Retrieve all products for a specific vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve products for.

    Returns:
        list[Product]: List of product objects.

    Raises:
        ValidationError: If vendor_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Fetching products for vendor_id: {vendor_id}")
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

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


def get_all_products(db: Database) -> list[Product]:
    """Retrieve all products.

    Args:
        db (Database): MongoDB database instance.

    Returns:
        list[Product]: List of all product objects.

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


def update_product(db: Database, product_id: str, vendor_id: str, update_data: dict) -> Product:
    """Update an existing product.

    Args:
        db (Database): MongoDB database instance.
        product_id (str): ID of the product to update.
        vendor_id (str): ID of the vendor updating the product.
        update_data (dict): Data to update in the product.

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
        if not ObjectId.is_valid(product_id):
            raise ValidationError(f"Invalid product ID format: {product_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        product = db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            logger.warning(f"Product with ID {product_id} not found")
            raise NotFoundError(f"Product with ID {product_id} not found")
        if product["vendor_id"] != vendor_id:
            logger.warning(f"Unauthorized update attempt on product {product_id} by vendor {vendor_id}")
            raise UnauthorizedError("You can only update your own products")

        if "price" in update_data and (not isinstance(update_data["price"], (int, float)) or update_data["price"] <= 0):
            raise ValidationError("Price must be a positive number")
        if "quantity" in update_data and (not isinstance(update_data["quantity"], int) or update_data["quantity"] < 0):
            raise ValidationError("Quantity must be a non-negative integer")
        if "category_id" in update_data:
            if not ObjectId.is_valid(update_data["category_id"]):
                raise ValidationError(f"Invalid category_id format: {update_data['category_id']}")
            if not db.product_categories.find_one({"_id": ObjectId(update_data["category_id"])}):
                raise ValidationError(f"Product category {update_data['category_id']} not found")

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = db.products.update_one({"_id": ObjectId(product_id)}, {"$set": update_data})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update product {product_id}")

        updated_product = db.products.find_one({"_id": ObjectId(product_id)})
        logger.info(f"Product updated successfully - ID: {product_id}, changes: {update_data}")
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
    except DuplicateKeyError as dke:
        logger.error(f"Duplicate key error in update_product: {str(dke)}, input: {update_data}")
        raise ValidationError("A product with this name already exists for this vendor")
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_product: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update product: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_product: {str(e)}, product_id: {product_id}, input: {update_data}",
                     exc_info=True)
        raise InternalServerError(f"Failed to update product: {str(e)}")


def delete_product(db: Database, product_id: str, vendor_id: str) -> dict:
    """Delete a product.

    Args:
        db (Database): MongoDB database instance.
        product_id (str): ID of the product to delete.
        vendor_id (str): ID of the vendor deleting the product.

    Returns:
        dict: Confirmation message of deletion.

    Raises:
        ValidationError: If product_id or vendor_id is invalid.
        NotFoundError: If product is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Deleting product with ID: {product_id} for vendor_id: {vendor_id}")
    try:
        if not ObjectId.is_valid(product_id):
            raise ValidationError(f"Invalid product ID format: {product_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        product = db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            logger.warning(f"Product with ID {product_id} not found")
            raise NotFoundError(f"Product with ID {product_id} not found")
        if product["vendor_id"] != vendor_id:
            logger.warning(f"Unauthorized delete attempt on product {product_id} by vendor {vendor_id}")
            raise UnauthorizedError("You can only delete your own products")

        db.products.delete_one({"_id": ObjectId(product_id)})
        db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$pull": {"products": product_id}})
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
        logger.error(f"Unexpected error in delete_product: {str(e)}, product_id: {product_id}, vendor_id: {vendor_id}",
                     exc_info=True)
        raise InternalServerError(f"Failed to delete product: {str(e)}")

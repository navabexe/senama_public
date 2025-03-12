# services/orders.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.order import Order
from domain.schemas.order import OrderCreate, OrderUpdate

logger = logging.getLogger(__name__)

def create_order(db: Database, user_id: str, order_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new order for a user with atomic check to prevent duplicates.

    Args:
        db (Database): MongoDB database instance.
        user_id (str): ID of the user creating the order.
        order_data (Dict[str, Any]): Data for the order including product_id and quantity.

    Returns:
        Dict[str, str]: Dictionary containing the created order ID.

    Raises:
        ValidationError: If required fields are missing, invalid, or order already exists.
        NotFoundError: If product is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Creating order for user_id: {user_id}, data: {order_data}")
    try:
        validate_object_id(user_id, "user_id")
        order_create = OrderCreate(**order_data)  # اعتبارسنجی با Pydantic
        order_data_validated = order_create.model_dump()

        validate_object_id(order_data_validated["product_id"], "product_id")

        product = db.products.find_one({"_id": ObjectId(order_data_validated["product_id"])})
        if not product:
            raise NotFoundError(f"Product with ID {order_data_validated['product_id']} not found")

        vendor_id = product["vendor_id"]
        order_data_validated["user_id"] = user_id
        order_data_validated["vendor_id"] = vendor_id
        order_data_validated["total_price"] = product["price"] * order_data_validated["quantity"]
        order = Order(**order_data_validated)

        with db.client.start_session() as session:
            with session.start_transaction():
                # بررسی اتمی برای جلوگیری از سفارش تکراری
                query = {
                    "user_id": user_id,
                    "product_id": order_data_validated["product_id"],
                    "quantity": order_data_validated["quantity"],
                    "status": "pending"  # فرض می‌کنیم سفارش تکراری فقط در حالت pending بررسی شود
                }
                existing_order = db.orders.find_one(query, session=session)
                if existing_order:
                    raise ValidationError(f"An order with this product and quantity already exists for user {user_id}")

                result = db.orders.insert_one(order.model_dump(exclude={"id"}), session=session)
                order_id = str(result.inserted_id)

        logger.info(f"Order created successfully - ID: {order_id}, user_id: {user_id}, vendor_id: {vendor_id}")
        return {"id": order_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_order: {ve.detail}, input: {order_data}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_order: {ne.detail}, product_id: {order_data.get('product_id')}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_order: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create order: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_order: {str(e)}, user_id: {user_id}, input: {order_data}", exc_info=True)
        raise InternalServerError(f"Failed to create order: {str(e)}")

def get_order(db: Database, order_id: str, user_id: str) -> Order:
    """Retrieve an order by its ID.

    Args:
        db (Database): MongoDB database instance.
        order_id (str): ID of the order to retrieve.
        user_id (str): ID of the user or vendor requesting the order.

    Returns:
        Order: The requested order object.

    Raises:
        ValidationError: If order_id or user_id is invalid.
        NotFoundError: If order is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Fetching order with ID: {order_id} for user_id: {user_id}")
    try:
        validate_object_id(order_id, "order_id")
        validate_object_id(user_id, "user_id")

        order = db.orders.find_one({"_id": ObjectId(order_id)})
        if not order:
            logger.warning(f"Order with ID {order_id} not found")
            raise NotFoundError(f"Order with ID {order_id} not found")
        if order["user_id"] != user_id and order["vendor_id"] != user_id:
            logger.warning(f"Unauthorized access attempt on order {order_id} by user {user_id}")
            raise UnauthorizedError("You can only view your own orders")

        logger.info(f"Order retrieved successfully - ID: {order_id}, user_id: {user_id}")
        return Order(**order)
    except ValidationError as ve:
        logger.error(f"Validation error in get_order: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_order: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_order: {ue.detail}, user_id: {user_id}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_order: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get order: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_order: {str(e)}, order_id: {order_id}", exc_info=True)
        raise InternalServerError(f"Failed to get order: {str(e)}")

def get_orders_by_user(db: Database, user_id: str) -> List[Order]:
    """Retrieve all orders for a specific user.

    Args:
        db (Database): MongoDB database instance.
        user_id (str): ID of the user to retrieve orders for.

    Returns:
        List[Order]: List of order objects.

    Raises:
        ValidationError: If user_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Fetching orders for user_id: {user_id}")
    try:
        validate_object_id(user_id, "user_id")

        orders = list(db.orders.find({"user_id": user_id}))
        if not orders:
            logger.debug(f"No orders found for user_id: {user_id}")
            return []

        logger.info(f"Retrieved {len(orders)} orders for user_id: {user_id}")
        return [Order(**order) for order in orders]
    except ValidationError as ve:
        logger.error(f"Validation error in get_orders_by_user: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_orders_by_user: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get orders: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_orders_by_user: {str(e)}, user_id: {user_id}", exc_info=True)
        raise InternalServerError(f"Failed to get orders: {str(e)}")

def get_orders_by_vendor(db: Database, vendor_id: str) -> List[Order]:
    """Retrieve all orders for a specific vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve orders for.

    Returns:
        List[Order]: List of order objects.

    Raises:
        ValidationError: If vendor_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Fetching orders for vendor_id: {vendor_id}")
    try:
        validate_object_id(vendor_id, "vendor_id")

        orders = list(db.orders.find({"vendor_id": vendor_id}))
        if not orders:
            logger.debug(f"No orders found for vendor_id: {vendor_id}")
            return []

        logger.info(f"Retrieved {len(orders)} orders for vendor_id: {vendor_id}")
        return [Order(**order) for order in orders]
    except ValidationError as ve:
        logger.error(f"Validation error in get_orders_by_vendor: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_orders_by_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get orders: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_orders_by_vendor: {str(e)}, vendor_id: {vendor_id}", exc_info=True)
        raise InternalServerError(f"Failed to get orders: {str(e)}")

def update_order(db: Database, order_id: str, user_id: str, update_data: Dict[str, Any]) -> Order:
    """Update an existing order.

    Args:
        db (Database): MongoDB database instance.
        order_id (str): ID of the order to update.
        user_id (str): ID of the user or vendor updating the order.
        update_data (Dict[str, Any]): Data to update in the order (e.g., status).

    Returns:
        Order: The updated order object.

    Raises:
        ValidationError: If order_id, user_id, or status is invalid.
        NotFoundError: If order is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Updating order with ID: {order_id} by user_id: {user_id}, data: {update_data}")
    try:
        validate_object_id(order_id, "order_id")
        validate_object_id(user_id, "user_id")
        order_update = OrderUpdate(**update_data)  # اعتبارسنجی با Pydantic
        update_data_validated = order_update.model_dump(exclude_unset=True)

        order = db.orders.find_one({"_id": ObjectId(order_id)})
        if not order:
            logger.warning(f"Order with ID {order_id} not found")
            raise NotFoundError(f"Order with ID {order_id} not found")
        if order["vendor_id"] != user_id:
            logger.warning(f"Unauthorized update attempt on order {order_id} by user {user_id}")
            raise UnauthorizedError("Only the vendor can update order status")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)
        updated = db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": update_data_validated})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update order {order_id}")

        updated_order = db.orders.find_one({"_id": ObjectId(order_id)})
        logger.info(f"Order updated successfully - ID: {order_id}, changes: {update_data_validated}")
        return Order(**updated_order)
    except ValidationError as ve:
        logger.error(f"Validation error in update_order: {ve.detail}, input: {update_data}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_order: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_order: {ue.detail}, user_id: {user_id}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_order: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update order: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_order: {str(e)}, order_id: {order_id}, input: {update_data}", exc_info=True)
        raise InternalServerError(f"Failed to update order: {str(e)}")

def delete_order(db: Database, order_id: str, user_id: str) -> Dict[str, str]:
    """Delete an order.

    Args:
        db (Database): MongoDB database instance.
        order_id (str): ID of the order to delete.
        user_id (str): ID of the user deleting the order.

    Returns:
        Dict[str, str]: Confirmation message of deletion.

    Raises:
        ValidationError: If order_id or user_id is invalid.
        NotFoundError: If order is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    logger.debug(f"Deleting order with ID: {order_id} by user_id: {user_id}")
    try:
        validate_object_id(order_id, "order_id")
        validate_object_id(user_id, "user_id")

        order = db.orders.find_one({"_id": ObjectId(order_id)})
        if not order:
            logger.warning(f"Order with ID {order_id} not found")
            raise NotFoundError(f"Order with ID {order_id} not found")
        if order["user_id"] != user_id:
            logger.warning(f"Unauthorized delete attempt on order {order_id} by user {user_id}")
            raise UnauthorizedError("You can only delete your own orders")

        db.orders.delete_one({"_id": ObjectId(order_id)})
        logger.info(f"Order deleted successfully - ID: {order_id} by user: {user_id}")
        return {"message": f"Order {order_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_order: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_order: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_order: {ue.detail}, user_id: {user_id}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_order: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete order: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_order: {str(e)}, order_id: {order_id}", exc_info=True)
        raise InternalServerError(f"Failed to delete order: {str(e)}")
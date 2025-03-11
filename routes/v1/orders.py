# routes/v1/orders.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.order import OrderCreate, OrderUpdate, OrderResponse
from infrastructure.database.client import get_db
from services.orders import create_order, get_order, get_orders_by_user, get_orders_by_vendor, update_order, delete_order
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new order")
@limiter.limit("5/minute")
async def create_order_route(
    request: Request,
    order_data: OrderCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Create a new order (user only)."""
    try:
        current_user = get_current_user(token, db)
        if "user" not in current_user["roles"]:
            raise UnauthorizedError("Only users can create orders")
        user_id = str(current_user["_id"])
        result = create_order(db, user_id, order_data.model_dump())
        logger.info(f"Order created by user {user_id}: {result['id']}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to create order: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{order_id}", response_model=OrderResponse, summary="Get order by ID")
@limiter.limit("10/minute")
async def get_order_route(
    request: Request,
    order_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Get an order by ID (user or vendor only)."""
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        order = get_order(db, order_id, user_id)
        logger.info(f"Order retrieved: {order_id} by user/vendor: {user_id}")
        return order
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve order {order_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/user/{user_id}", response_model=list[OrderResponse], summary="Get all orders by user")
@limiter.limit("10/minute")
async def get_user_orders_route(
    request: Request,
    user_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Get all orders for a specific user (user only)."""
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        if requester_id != user_id and "admin" not in current_user["roles"]:
            raise UnauthorizedError("You can only view your own orders unless you are an admin")
        orders = get_orders_by_user(db, user_id)
        logger.info(f"Retrieved {len(orders)} orders for user: {user_id}")
        return orders
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve orders for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/vendor/{vendor_id}", response_model=list[OrderResponse], summary="Get all orders by vendor")
@limiter.limit("10/minute")
async def get_vendor_orders_route(
    request: Request,
    vendor_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Get all orders for a specific vendor (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        if requester_id != vendor_id and "admin" not in current_user["roles"]:
            raise UnauthorizedError("You can only view your own orders unless you are an admin")
        orders = get_orders_by_vendor(db, vendor_id)
        logger.info(f"Retrieved {len(orders)} orders for vendor: {vendor_id}")
        return orders
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve orders for vendor {vendor_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{order_id}", response_model=OrderResponse, summary="Update order")
@limiter.limit("5/minute")
async def update_order_route(
    request: Request,
    order_id: str,
    update_data: OrderUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Update an order (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can update orders")
        user_id = str(current_user["_id"])
        order = update_order(db, order_id, user_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Order updated: {order_id} by vendor: {user_id}")
        return order
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to update order {order_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{order_id}", response_model=dict, summary="Delete order")
@limiter.limit("5/minute")
async def delete_order_route(
    request: Request,
    order_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Delete an order (user only)."""
    try:
        current_user = get_current_user(token, db)
        if "user" not in current_user["roles"]:
            raise UnauthorizedError("Only users can delete orders")
        user_id = str(current_user["_id"])
        result = delete_order(db, order_id, user_id)
        logger.info(f"Order deleted: {order_id} by user: {user_id}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to delete order {order_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
# routes/v1/orders.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.orders import create_order, get_order, update_order, delete_order
from domain.schemas.order import OrderCreate, OrderUpdate, OrderResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new order", description="Creates a new order for the authenticated user.")
@limiter.limit("5/minute")
async def create_order_route(request: Request, order_data: OrderCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "user" not in current_user["roles"]:
        raise UnauthorizedError("Only users can create orders")
    return create_order(db, str(current_user["_id"]), order_data.dict())

@router.get("/{order_id}", response_model=OrderResponse, summary="Get order by ID", description="Retrieves an order by its ID for the user or vendor.")
@limiter.limit("10/minute")
async def get_order_route(request: Request, order_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_order(db, order_id, str(current_user["_id"]))

@router.put("/{order_id}", response_model=OrderResponse, summary="Update order", description="Updates order status or notes by the vendor.")
@limiter.limit("5/minute")
async def update_order_route(request: Request, order_id: str, update_data: OrderUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can update orders")
    return update_order(db, order_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{order_id}", response_model=dict, summary="Delete order", description="Deletes an order by its ID for the user.")
@limiter.limit("5/minute")
async def delete_order_route(request: Request, order_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "user" not in current_user["roles"]:
        raise UnauthorizedError("Only users can delete orders")
    return delete_order(db, order_id, str(current_user["_id"]))
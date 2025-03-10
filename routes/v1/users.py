# routes/v1/users.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.errors import UnauthorizedError
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.users import create_user, get_user, update_user, delete_user
from domain.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new user", description="Creates a new user with the provided data.")
@limiter.limit("5/minute")
async def create_user_route(request: Request, user_data: UserCreate, db: Database = Depends(get_db)):
    return create_user(db, user_data.dict())

@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID", description="Retrieves a user by their ID.")
@limiter.limit("10/minute")
async def get_user_route(request: Request, user_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_user(db, user_id)

@router.put("/{user_id}", response_model=UserResponse, summary="Update user", description="Updates user details.")
@limiter.limit("5/minute")
async def update_user_route(request: Request, user_id: str, update_data: UserUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if str(current_user["_id"]) != user_id:
        raise UnauthorizedError("You can only update your own profile")
    return update_user(db, user_id, update_data.dict(exclude_unset=True))

@router.delete("/{user_id}", response_model=dict, summary="Delete user", description="Deletes a user by their ID.")
@limiter.limit("5/minute")
async def delete_user_route(request: Request, user_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if str(current_user["_id"]) != user_id:
        raise UnauthorizedError("You can only delete your own profile")
    return delete_user(db, user_id)
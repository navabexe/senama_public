# routes/v1/users.py
import logging

from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.user import UserCreate, UserUpdate, UserResponse
from infrastructure.database.client import get_db
from services.users import UserService  # Import the UserService class

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

# Dependency to get UserService instance
def get_user_service(db: Database = Depends(get_db)) -> UserService:
    return UserService(db)

@router.post("", response_model=dict, summary="Create a new user")
@limiter.limit("5/minute")
async def create_user_route(
        request: Request,
        user_data: UserCreate,
        user_service: UserService = Depends(get_user_service)
):
    """Create a new user (accessible by anyone)."""
    try:
        result = user_service.create_user(user_data.model_dump())
        logger.info(f"User creation initiated: {result['id']}")
        return result
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
@limiter.limit("10/minute")
async def get_user_route(
        request: Request,
        user_id: str,
        user_service: UserService = Depends(get_user_service),
        token: str = Depends(get_token)
):
    """Get a user by ID (user or admin only)."""
    try:
        current_user = get_current_user(token, user_service.db)
        requester_id = str(current_user["_id"])
        user = user_service.get_user(user_id, requester_id)
        logger.info(f"User retrieved: {user_id} by requester: {requester_id}")
        return user
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
        logger.error(f"Failed to retrieve user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{user_id}", response_model=UserResponse, summary="Update user")
@limiter.limit("5/minute")
async def update_user_route(
        request: Request,
        user_id: str,
        update_data: UserUpdate,
        user_service: UserService = Depends(get_user_service),
        token: str = Depends(get_token)
):
    """Update a user (user or admin only)."""
    try:
        current_user = get_current_user(token, user_service.db)
        requester_id = str(current_user["_id"])
        user = user_service.update_user(user_id, requester_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"User updated: {user_id} by requester: {requester_id}")
        return user
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
        logger.error(f"Failed to update user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{user_id}", response_model=dict, summary="Delete user")
@limiter.limit("5/minute")
async def delete_user_route(
        request: Request,
        user_id: str,
        user_service: UserService = Depends(get_user_service),
        token: str = Depends(get_token)
):
    """Delete a user (user or admin only)."""
    try:
        current_user = get_current_user(token, user_service.db)
        requester_id = str(current_user["_id"])
        result = user_service.delete_user(user_id, requester_id)
        logger.info(f"User deleted: {user_id} by requester: {requester_id}")
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
        logger.error(f"Failed to delete user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
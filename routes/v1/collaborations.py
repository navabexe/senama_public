# routes/v1/blocked_users.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.block import BlockCreate, BlockResponse
from infrastructure.database.client import get_db
from services.blocked_users import create_block, get_block, get_blocked_users, update_block, delete_block
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new block")
@limiter.limit("5/minute")
async def create_block_route(
    request: Request,
    block_data: BlockCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        blocker_id = str(current_user["_id"])
        result = create_block(db, blocker_id, block_data.model_dump())
        logger.info(f"Block created by user {blocker_id}: {result['id']}")
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
        logger.error(f"Failed to create block: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{block_id}", response_model=BlockResponse, summary="Get block by ID")
@limiter.limit("10/minute")
async def get_block_route(
    request: Request,
    block_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        blocker_id = str(current_user["_id"])
        block = get_block(db, block_id, blocker_id)
        logger.info(f"Block retrieved: {block_id} by user: {blocker_id}")
        return block
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
        logger.error(f"Failed to retrieve block {block_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=list[BlockResponse], summary="Get all blocked users by blocker")
@limiter.limit("10/minute")
async def get_blocked_users_route(
    request: Request,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        blocker_id = str(current_user["_id"])
        blocked_users = get_blocked_users(db, blocker_id)
        logger.info(f"Retrieved {len(blocked_users)} blocked users for blocker: {blocker_id}")
        return blocked_users
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve blocked users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{block_id}", response_model=BlockResponse, summary="Update block")
@limiter.limit("5/minute")
async def update_block_route(
    request: Request,
    block_id: str,
    update_data: dict,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        blocker_id = str(current_user["_id"])
        block = update_block(db, block_id, blocker_id, update_data)
        logger.info(f"Block updated: {block_id} by user: {blocker_id}")
        return block
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
        logger.error(f"Failed to update block {block_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{block_id}", response_model=dict, summary="Delete block")
@limiter.limit("5/minute")
async def delete_block_route(
    request: Request,
    block_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        blocker_id = str(current_user["_id"])
        result = delete_block(db, block_id, blocker_id)
        logger.info(f"Block deleted: {block_id} by user: {blocker_id}")
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
        logger.error(f"Failed to delete block {block_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
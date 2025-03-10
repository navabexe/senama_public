# routes/v1/blocked_users.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.blocked_users import create_block, get_block, update_block, delete_block
from domain.schemas.block import BlockCreate, BlockUpdate, BlockResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Block a user or vendor", description="Creates a new block entry for the authenticated user or vendor.")
@limiter.limit("5/minute")
async def create_block_route(request: Request, block_data: BlockCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return create_block(db, str(current_user["_id"]), block_data.dict())

@router.get("/{block_id}", response_model=BlockResponse, summary="Get block by ID", description="Retrieves a block entry by its ID for the authenticated user or vendor.")
@limiter.limit("10/minute")
async def get_block_route(request: Request, block_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_block(db, block_id, str(current_user["_id"]))

@router.put("/{block_id}", response_model=BlockResponse, summary="Update block", description="Updates block details (e.g., reason) for the authenticated user or vendor.")
@limiter.limit("5/minute")
async def update_block_route(request: Request, block_id: str, update_data: BlockUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return update_block(db, block_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{block_id}", response_model=dict, summary="Delete block", description="Deletes a block entry for the authenticated user or vendor.")
@limiter.limit("5/minute")
async def delete_block_route(request: Request, block_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return delete_block(db, block_id, str(current_user["_id"]))
# routes/v1/collaborations.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.collaborations import create_collaboration, get_collaboration, update_collaboration, delete_collaboration
from domain.schemas.collaboration import CollaborationCreate, CollaborationUpdate, CollaborationResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new collaboration", description="Creates a new collaboration request to link a product.")
@limiter.limit("5/minute")
async def create_collaboration_route(request: Request, collaboration_data: CollaborationCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can create collaborations")
    return create_collaboration(db, str(current_user["_id"]), collaboration_data.dict())

@router.get("/{collaboration_id}", response_model=CollaborationResponse, summary="Get collaboration by ID", description="Retrieves a collaboration by its ID for the requester or target vendor.")
@limiter.limit("10/minute")
async def get_collaboration_route(request: Request, collaboration_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can view collaborations")
    return get_collaboration(db, collaboration_id, str(current_user["_id"]))

@router.put("/{collaboration_id}", response_model=CollaborationResponse, summary="Update collaboration", description="Updates collaboration status (e.g., accept/reject) by the target vendor.")
@limiter.limit("5/minute")
async def update_collaboration_route(request: Request, collaboration_id: str, update_data: CollaborationUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can update collaborations")
    return update_collaboration(db, collaboration_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{collaboration_id}", response_model=dict, summary="Delete collaboration", description="Deletes a pending collaboration by the requester vendor.")
@limiter.limit("5/minute")
async def delete_collaboration_route(request: Request, collaboration_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can delete collaborations")
    return delete_collaboration(db, collaboration_id, str(current_user["_id"]))
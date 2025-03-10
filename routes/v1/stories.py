# routes/v1/stories.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.stories import create_story, get_story, update_story, delete_story
from domain.schemas.story import StoryCreate, StoryUpdate, StoryResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new story", description="Creates a new story for the authenticated vendor. Expires in 24 hours by default.")
@limiter.limit("5/minute")
async def create_story_route(request: Request, story_data: StoryCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can create stories")
    return create_story(db, str(current_user["_id"]), story_data.dict())

@router.get("/{story_id}", response_model=StoryResponse, summary="Get story by ID", description="Retrieves a story by its ID. Updates status to 'expired' if past expiration.")
@limiter.limit("10/minute")
async def get_story_route(request: Request, story_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_story(db, story_id)

@router.put("/{story_id}", response_model=StoryResponse, summary="Update story", description="Updates story details for the authenticated vendor.")
@limiter.limit("5/minute")
async def update_story_route(request: Request, story_id: str, update_data: StoryUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can update stories")
    return update_story(db, story_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{story_id}", response_model=dict, summary="Delete story", description="Deletes a story by its ID for the authenticated vendor.")
@limiter.limit("5/minute")
async def delete_story_route(request: Request, story_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can delete stories")
    return delete_story(db, story_id, str(current_user["_id"]))
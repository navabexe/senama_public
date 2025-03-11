# routes/v1/stories.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.story import StoryCreate, StoryUpdate, StoryResponse
from infrastructure.database.client import get_db
from services.stories import create_story, get_story, get_stories_by_vendor, get_all_stories, update_story, delete_story
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new story")
@limiter.limit("5/minute")
async def create_story_route(
    request: Request,
    story_data: StoryCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Create a new story (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can create stories")
        vendor_id = str(current_user["_id"])
        result = create_story(db, vendor_id, story_data.model_dump())
        logger.info(f"Story created by vendor {vendor_id}: {result['id']}")
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
        logger.error(f"Failed to create story: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{story_id}", response_model=StoryResponse, summary="Get story by ID")
@limiter.limit("10/minute")
async def get_story_route(
    request: Request,
    story_id: str,
    db: Database = Depends(get_db)
):
    """Get a story by ID (public access)."""
    try:
        story = get_story(db, story_id)
        logger.info(f"Story retrieved: {story_id}")
        return story
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve story {story_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/vendor/{vendor_id}", response_model=list[StoryResponse], summary="Get all stories by vendor")
@limiter.limit("10/minute")
async def get_vendor_stories_route(
    request: Request,
    vendor_id: str,
    db: Database = Depends(get_db)
):
    """Get all stories for a specific vendor (public access)."""
    try:
        stories = get_stories_by_vendor(db, vendor_id)
        logger.info(f"Retrieved {len(stories)} stories for vendor: {vendor_id}")
        return stories
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve stories for vendor {vendor_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=list[StoryResponse], summary="Get all active stories")
@limiter.limit("10/minute")
async def get_all_stories_route(
    request: Request,
    db: Database = Depends(get_db)
):
    """Get all active stories (public access)."""
    try:
        stories = get_all_stories(db)
        logger.info(f"Retrieved {len(stories)} active stories")
        return stories
    except Exception as e:
        logger.error(f"Failed to retrieve all stories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{story_id}", response_model=StoryResponse, summary="Update story")
@limiter.limit("5/minute")
async def update_story_route(
    request: Request,
    story_id: str,
    update_data: StoryUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Update a story (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can update stories")
        vendor_id = str(current_user["_id"])
        story = update_story(db, story_id, vendor_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Story updated: {story_id} by vendor: {vendor_id}")
        return story
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
        logger.error(f"Failed to update story {story_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{story_id}", response_model=dict, summary="Delete story")
@limiter.limit("5/minute")
async def delete_story_route(
    request: Request,
    story_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    """Delete a story (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can delete stories")
        vendor_id = str(current_user["_id"])
        result = delete_story(db, story_id, vendor_id)
        logger.info(f"Story deleted: {story_id} by vendor: {vendor_id}")
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
        logger.error(f"Failed to delete story {story_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
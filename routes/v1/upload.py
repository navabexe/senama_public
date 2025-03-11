# routes/v1/upload.py
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from infrastructure.database.client import get_db
from services.upload import UploadService
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("/file", response_model=dict, summary="Upload a file")
@limiter.limit("5/minute")
async def upload_file_route(
    request: Request,
    file: UploadFile = File(...),
    entity_type: str = Depends(lambda x: x.query_params.get("entity_type")),
    entity_id: str = Depends(lambda x: x.query_params.get("entity_id")),
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        upload_service = UploadService(db)
        result = await upload_service.upload_file(user_id, file, entity_type, entity_id)
        logger.info(f"File uploaded by user {user_id} for {entity_type} {entity_id}: {result['file_url']}")
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
        logger.error(f"Failed to upload file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cleanup", response_model=dict, summary="Clean up unused files")
@limiter.limit("1/minute")
async def cleanup_unused_files_route(
    request: Request,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can clean up unused files")
        upload_service = UploadService(db)
        result = upload_service.cleanup_unused_files()
        logger.info(f"Unused files cleaned up by admin {current_user['_id']}: {result['message']}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except Exception as e:
        logger.error(f"Failed to clean up unused files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
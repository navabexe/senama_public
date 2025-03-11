# routes/v1/sessions.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.session import SessionCreate, SessionUpdate, SessionResponse
from infrastructure.database.client import get_db
from services.sessions import create_session, get_session, get_sessions_by_user, update_session, revoke_session, delete_session, cleanup_expired_sessions
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new session")
@limiter.limit("5/minute")
async def create_session_route(
    request: Request,
    session_data: SessionCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        result = create_session(db, user_id, session_data.model_dump())
        logger.info(f"Session created by user {user_id}: {result['id']}")
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
        logger.error(f"Failed to create session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{session_id}", response_model=SessionResponse, summary="Get session by ID")
@limiter.limit("10/minute")
async def get_session_route(
    request: Request,
    session_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        session = get_session(db, session_id, user_id)
        logger.info(f"Session retrieved: {session_id} by user: {user_id}")
        return session
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
        logger.error(f"Failed to retrieve session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/user/{user_id}", response_model=list[SessionResponse], summary="Get all sessions by user")
@limiter.limit("10/minute")
async def get_user_sessions_route(
    request: Request,
    user_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        if requester_id != user_id and "admin" not in current_user["roles"]:
            raise UnauthorizedError("You can only view your own sessions unless you are an admin")
        sessions = get_sessions_by_user(db, user_id)
        logger.info(f"Retrieved {len(sessions)} sessions for user: {user_id}")
        return sessions
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve sessions for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{session_id}", response_model=SessionResponse, summary="Update session")
@limiter.limit("5/minute")
async def update_session_route(
    request: Request,
    session_id: str,
    update_data: SessionUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        session = update_session(db, session_id, user_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Session updated: {session_id} by user: {user_id}")
        return session
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
        logger.error(f"Failed to update session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{session_id}/revoke", response_model=dict, summary="Revoke session")
@limiter.limit("5/minute")
async def revoke_session_route(
    request: Request,
    session_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        result = revoke_session(db, session_id, user_id)
        logger.info(f"Session revoked: {session_id} by user: {user_id}")
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
        logger.error(f"Failed to revoke session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{session_id}", response_model=dict, summary="Delete session")
@limiter.limit("5/minute")
async def delete_session_route(
    request: Request,
    session_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        result = delete_session(db, session_id, user_id)
        logger.info(f"Session deleted: {session_id} by user: {user_id}")
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
        logger.error(f"Failed to delete session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cleanup", response_model=dict, summary="Clean up expired sessions")
@limiter.limit("1/minute")
async def cleanup_expired_sessions_route(
    request: Request,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can clean up expired sessions")
        result = cleanup_expired_sessions(db)
        logger.info(f"Expired sessions cleaned up by admin {current_user['_id']}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except Exception as e:
        logger.error(f"Failed to clean up expired sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
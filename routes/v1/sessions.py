# routes/v1/sessions.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.sessions import create_session, get_session, update_session, delete_session
from domain.schemas.session import SessionCreate, SessionUpdate, SessionResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new session", description="Creates a new session for the authenticated user or vendor.")
@limiter.limit("5/minute")
async def create_session_route(request: Request, session_data: SessionCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return create_session(db, str(current_user["_id"]), session_data.dict())

@router.get("/{session_id}", response_model=SessionResponse, summary="Get session by ID", description="Retrieves a session by its ID for the authenticated user or vendor.")
@limiter.limit("10/minute")
async def get_session_route(request: Request, session_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_session(db, session_id, str(current_user["_id"]))

@router.put("/{session_id}", response_model=SessionResponse, summary="Update session", description="Updates session status or details for the authenticated user or vendor.")
@limiter.limit("5/minute")
async def update_session_route(request: Request, session_id: str, update_data: SessionUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return update_session(db, session_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{session_id}", response_model=dict, summary="Delete session", description="Deletes a session for the authenticated user or vendor.")
@limiter.limit("5/minute")
async def delete_session_route(request: Request, session_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return delete_session(db, session_id, str(current_user["_id"]))
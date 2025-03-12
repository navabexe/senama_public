# routes/v1/auth.py
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config.settings import settings
from core.auth.auth import get_token
from core.auth.jwt import decode_token
from core.auth.otp import generate_otp, save_otp, verify_otp
from core.errors import ValidationError
from domain.schemas.session import SessionResponse
from infrastructure.database.client import get_db
from services.auth import AuthService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

def get_auth_service(db: Database = Depends(get_db)) -> AuthService:
    return AuthService(db)

@router.post("/register", response_model=SessionResponse)
@limiter.limit("5/minute")
async def register(
        request: Request,
        phone: str,
        auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user and send OTP."""
    try:
        user = auth_service.register_user(phone, "user")
        otp = generate_otp()
        save_otp(auth_service.db, phone, otp)
        logger.info(f"User registered with phone {phone}, OTP: {otp}")
        return SessionResponse(**{
            "_id": user["user_id"],
            "user_id": user["user_id"],
            "access_token": None,
            "refresh_token": None,
            "status": "pending",
            "device_info": request.headers.get("User-Agent", "unknown"),
            "expires_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to register phone {phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/login", response_model=SessionResponse)
@limiter.limit("5/minute")
async def login(
        request: Request,
        phone: str,
        auth_service: AuthService = Depends(get_auth_service)
):
    """Initiate login and send OTP."""
    try:
        login_response = auth_service.login(phone)
        user_id = login_response["id"]
        logger.info(f"Login initiated for phone {phone}")
        return SessionResponse(**{
            "_id": user_id,
            "user_id": user_id,
            "access_token": None,
            "refresh_token": None,
            "status": "pending",
            "device_info": request.headers.get("User-Agent", "unknown"),
            "expires_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to login phone {phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/verify", response_model=SessionResponse)
@limiter.limit("5/minute")
async def verify(
        request: Request,
        phone: str,
        otp: str,
        auth_service: AuthService = Depends(get_auth_service)
):
    """Verify OTP and complete login."""
    try:
        if not verify_otp(auth_service.db, phone, otp):
            raise HTTPException(status_code=400, detail="Invalid OTP")

        login_response = auth_service.verify_login(phone)
        user_id = login_response["id"]
        access_token = login_response["access_token"]
        refresh_token = login_response["refresh_token"]

        session = {
            "_id": user_id,
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "status": "active",
            "device_info": request.headers.get("User-Agent", "unknown"),
            "expires_at": datetime.fromtimestamp(decode_token(access_token, settings.SECRET_KEY)["exp"]),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        logger.info(f"User {phone} verified, session: {user_id}")
        return SessionResponse(**session)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to verify OTP for phone {phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/refresh", response_model=SessionResponse)
@limiter.limit("10/minute")
async def refresh_token(
        request: Request,
        token: str = Depends(get_token),
        auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh an access token using a refresh token."""
    try:
        refresh_response = auth_service.refresh_token(token)
        session = auth_service.db.sessions.find_one({"refresh_token": token})
        if not session:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        updated_session = {
            **session,
            "access_token": refresh_response["access_token"],
            "updated_at": datetime.now(timezone.utc)
        }
        logger.info(f"Token refreshed for user {session['user_id']}")
        return SessionResponse(**updated_session)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/logout", response_model=dict)
@limiter.limit("5/minute")
async def logout(
        request: Request,
        token: str = Depends(get_token),
        auth_service: AuthService = Depends(get_auth_service)
):
    """Logout a user by revoking their session."""
    try:
        session = auth_service.db.sessions.find_one({"access_token": token})
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")

        auth_service.db.sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"status": "revoked", "updated_at": datetime.now(timezone.utc)}}
        )
        logger.info(f"User {session['user_id']} logged out, session: {session['_id']}")
        return {"message": "Logged out successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to logout: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
# routes/v1/auth.py
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config.settings import settings
from core.auth.auth import get_token
from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.auth.otp import generate_otp, save_otp, verify_otp
from core.utils.db import DBHelper
from domain.schemas.session import SessionResponse
from services.auth import register_user, verify_login

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


def get_db() -> Database:
    return DBHelper().db


@router.post("/register", response_model=SessionResponse)
@limiter.limit("5/minute")
async def register(
        request: str,  # Required for limiter
        phone: str,
        db: Database = Depends(get_db)
):
    """Register a new user and send OTP."""
    try:
        user = register_user(db, phone)
        otp = generate_otp()
        save_otp(db, phone, otp)
        # Simulate sending OTP (e.g., via SMS or email)
        logger.info(f"User registered with phone {phone}, OTP generated: {otp}")
        return SessionResponse(**user)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to register user with phone {phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=SessionResponse)
@limiter.limit("5/minute")
async def login(
        request: str,  # Required for limiter
        phone: str,
        db: Database = Depends(get_db)
):
    """Initiate login and send OTP."""
    try:
        user = login_user(db, phone)
        otp = generate_otp()
        save_otp(db, phone, otp)
        # Simulate sending OTP (e.g., via SMS or email)
        logger.info(f"Login initiated for phone {phone}, OTP generated: {otp}")
        return SessionResponse(**user)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to initiate login for phone {phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/verify", response_model=SessionResponse)
@limiter.limit("5/minute")
async def verify(
        request: str,  # Required for limiter
        phone: str,
        otp: str,
        db: Database = Depends(get_db)
):
    """Verify OTP and complete login."""
    try:
        if not verify_otp(db, phone, otp):
            raise HTTPException(status_code=400, detail="Invalid OTP")

        user = verify_login(db, phone)
        access_token = create_access_token(user["_id"], user["roles"])
        refresh_token = create_refresh_token(user["_id"], user["roles"])

        session = {
            "_id": user["_id"],
            "user_id": user["_id"],
            "access_token": access_token,
            "refresh_token": refresh_token,
            "status": "active",
            "device_info": request.headers.get("User-Agent", "unknown"),
            "expires_at": datetime.fromtimestamp(decode_token(access_token, settings.SECRET_KEY)["exp"]),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        db.sessions.insert_one(session)

        logger.info(f"User {phone} verified and logged in, session created: {session['_id']}")
        return SessionResponse(**session)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to verify OTP for phone {phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/refresh", response_model=SessionResponse)
@limiter.limit("10/minute")
async def refresh_token(
        request: str,  # Required for limiter
        token: str = Depends(get_token),
        db: Database = Depends(get_db)
):
    """Refresh an access token using a refresh token."""
    try:
        payload = decode_token(token, settings.REFRESH_SECRET_KEY)
        user_id = payload["sub"]
        roles = payload["roles"]

        user = db.users.find_one({"_id": user_id}) or db.vendors.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")

        access_token = create_access_token(user_id, roles)
        session = db.sessions.find_one({"refresh_token": token})
        if not session:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        db.sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"access_token": access_token, "updated_at": datetime.now(timezone.utc)}}
        )
        updated_session = db.sessions.find_one({"_id": session["_id"]})

        logger.info(f"Token refreshed for user {user_id}")
        return SessionResponse(**updated_session)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout", response_model=dict)
@limiter.limit("5/minute")
async def logout(
        request: str,  # Required for limiter
        token: str = Depends(get_token),
        db: Database = Depends(get_db)
):
    """Logout a user by revoking their session."""
    try:
        session = db.sessions.find_one({"access_token": token})
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")

        db.sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"status": "revoked", "updated_at": datetime.now(timezone.utc)}}
        )

        logger.info(f"User {session['user_id']} logged out, session revoked: {session['_id']}")
        return {"message": "Logged out successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to logout: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

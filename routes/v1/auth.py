import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_token
from core.errors import ValidationError, NotFoundError
from domain.schemas.auth import RegisterRequest
from domain.schemas.session import SessionResponse
from infrastructure.database.client import get_db
from services.auth import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

def get_auth_service(db: Database = Depends(get_db)) -> AuthService:
    return AuthService(db)

@router.post("/request_otp", response_model=dict)
@limiter.limit("5/minute")
async def request_otp(
        request: Request,
        phone: str = Body(..., embed=True),
        auth_service: AuthService = Depends(get_auth_service)
):
    """Send an OTP to the provided phone number."""
    try:
        return auth_service.request_otp(phone)
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to send OTP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/register", response_model=dict)
@limiter.limit("5/minute")
async def register(
        request: Request,
        data: RegisterRequest,
        auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user or vendor and send an OTP for verification."""
    try:
        return auth_service.register(data.model_dump())
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to register: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/verify", response_model=SessionResponse)
@limiter.limit("5/minute")
async def verify(
        request: Request,
        phone: str = Body(..., embed=True),
        otp: str = Body(..., embed=True),
        auth_service: AuthService = Depends(get_auth_service)
):
    """Verify the OTP and activate the user/vendor account."""
    try:
        return auth_service.verify_registration(phone, otp)
    except NotFoundError as ne:
        raise HTTPException(status_code=404, detail=ne.detail)
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to verify OTP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/refresh", response_model=SessionResponse)
@limiter.limit("10/minute")
async def refresh_token(
        request: Request,
        token: str = Depends(get_token),
        auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh the access token using a valid refresh token."""
    try:
        return auth_service.refresh_token(token)
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
    """Logout the user by revoking the access token."""
    try:
        return auth_service.logout(token)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to logout: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

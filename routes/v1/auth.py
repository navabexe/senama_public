# routes/v1/auth.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.routes.v1.users import TokenResponse, OTPSendRequest, OTPVerifyRequest
from infrastructure.database.client import get_db
from services.auth import send_otp, verify_otp_and_login

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/send-otp", response_model=dict)
@limiter.limit("5/minute")
async def send_otp_route(request: Request, otp_request: OTPSendRequest, db: Database = Depends(get_db)):
    return send_otp(db, otp_request.phone)

@router.post("/verify-otp", response_model=TokenResponse)
@limiter.limit("5/minute")
async def verify_otp_route(request: Request, otp_request: OTPVerifyRequest, db: Database = Depends(get_db)):
    result = verify_otp_and_login(db, otp_request.phone, otp_request.otp)
    return TokenResponse(**result)
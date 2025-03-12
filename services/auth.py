import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from bson import ObjectId
from fastapi import APIRouter
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config.settings import settings
from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.auth.otp import generate_otp, save_otp, verify_otp
from core.errors import ValidationError, InternalServerError, NotFoundError
from domain.schemas.session import SessionCreate

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

class AuthService:
    """Service class for authentication-related operations."""

    def __init__(self, db: Database):
        self.db = db

    def request_otp(self, phone: str) -> Dict[str, str]:
        """Send OTP for authentication or registration."""
        try:
            if not phone.startswith("+"):
                raise ValidationError("Invalid phone number format")

            otp = generate_otp()
            save_otp(self.db, phone, otp)
            logger.info(f"User registered with phone {phone}, OTP generated: {otp}")
            return {"message": "OTP sent successfully"}
        except ValidationError as ve:
            raise ve
        except Exception as e:
            raise InternalServerError(f"Failed to send OTP: {str(e)}")

    def register(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Register a new user or vendor and send an OTP."""
        try:
            if "role" not in data or data["role"] not in ["user", "vendor"]:
                raise ValidationError("Invalid role. Must be 'user' or 'vendor'.")

            if data["role"] == "vendor":
                return self.register_vendor(data)
            return self.register_user(data)
        except ValidationError as ve:
            raise ve
        except Exception as e:
            raise InternalServerError(f"Failed to register: {str(e)}")

    def register_vendor(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Register a new vendor and send an OTP."""
        try:
            required_fields = ["name", "owner_name", "address", "location", "city", "province", "business_category_ids"]
            for field in required_fields:
                if not data.get(field):
                    raise ValidationError(f"{field} is required")

            existing_vendor = self.db.vendors.find_one({"owner_phone": data["phone"]})
            if existing_vendor:
                if existing_vendor["status"] == "pending":
                    return self.request_otp(data["phone"])
                else:
                    raise ValidationError("Phone number is already registered and verified.")

            data["roles"] = ["vendor"]
            data["status"] = "pending"
            data["created_at"] = datetime.now(timezone.utc)
            data["updated_at"] = datetime.now(timezone.utc)

            result = self.db.vendors.insert_one(data)
            vendor_id = str(result.inserted_id)
            self.request_otp(data["phone"])

            return {"message": "OTP sent successfully", "vendor_id": vendor_id}
        except ValidationError as ve:
            raise ve
        except Exception as e:
            raise InternalServerError(f"Failed to register vendor: {str(e)}")

    def register_user(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Register a new user and send an OTP."""
        try:
            if not data.get("phone"):
                raise ValidationError("Phone number is required")

            existing_user = self.db.users.find_one({"phone": data["phone"]})
            if existing_user:
                if existing_user["status"] == "pending":
                    return self.request_otp(data["phone"])
                else:
                    raise ValidationError("Phone number is already registered and verified.")

            data["roles"] = ["user"]
            data["status"] = "pending"
            data["created_at"] = datetime.now(timezone.utc)
            data["updated_at"] = datetime.now(timezone.utc)

            result = self.db.users.insert_one(data)
            user_id = str(result.inserted_id)
            self.request_otp(data["phone"])

            return {"message": "OTP sent successfully", "user_id": user_id}
        except ValidationError as ve:
            raise ve
        except Exception as e:
            raise InternalServerError(f"Failed to register user: {str(e)}")

    def verify_registration(self, phone: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and activate the user/vendor account."""
        try:
            if not verify_otp(self.db, phone, otp):
                raise ValidationError("Invalid or expired OTP. Please request a new one.")

            user = self.db.users.find_one({"phone": phone})
            if not user:
                user = self.db.vendors.find_one({"owner_phone": phone})
            if not user:
                raise NotFoundError("User not found. Please register first.")
            if user["status"] == "active":
                raise ValidationError("User is already verified. Please log in.")

            self.db.users.update_one({"_id": user["_id"]}, {"$set": {"status": "active"}})
            access_token = create_access_token(str(user["_id"]), user["roles"])
            refresh_token = create_refresh_token(str(user["_id"]), user["roles"])

            return {
                "message": "Registration completed successfully",
                "id": str(user["_id"]),
                "access_token": access_token,
                "status": "active",
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        except NotFoundError as ne:
            raise ne
        except ValidationError as ve:
            raise ve
        except Exception as e:
            raise InternalServerError(f"Failed to verify registration: {str(e)}")

    def refresh_token(self, token: str) -> Dict[str, str]:
        """Refresh the access token using a valid refresh token."""
        try:
            payload = decode_token(token, settings.REFRESH_SECRET_KEY)
            user_id = payload.get("sub")
            if not user_id or not ObjectId.is_valid(user_id):
                raise ValidationError("Invalid refresh token.")

            session = self.db.sessions.find_one({"user_id": user_id, "refresh_token": token})
            if not session or session.get("status") != "active":
                raise ValidationError("Invalid or expired refresh token.")

            user = self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                user = self.db.vendors.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise NotFoundError("User not found.")

            new_access_token = create_access_token(user_id, user.get("roles", []))
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

            self.db.sessions.update_one(
                {"user_id": user_id, "refresh_token": token},
                {"$set": {"access_token": new_access_token, "expires_at": expires_at,
                          "updated_at": datetime.now(timezone.utc)}}
            )

            return {"access_token": new_access_token, "refresh_token": token}
        except ValidationError as ve:
            raise ve
        except NotFoundError as ne:
            raise ne
        except Exception as e:
            raise InternalServerError(f"Failed to refresh token: {str(e)}")

    def logout(self, token: str) -> Dict[str, str]:
        """Logout the user by revoking the access token."""
        try:
            session = self.db.sessions.find_one({"access_token": token})
            if not session:
                raise NotFoundError("Session not found.")

            self.db.sessions.update_one(
                {"access_token": token},
                {"$set": {"status": "revoked", "updated_at": datetime.now(timezone.utc)}}
            )
            return {"message": "Logged out successfully"}
        except NotFoundError as ne:
            raise ne
        except Exception as e:
            raise InternalServerError(f"Failed to logout: {str(e)}")

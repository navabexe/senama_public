# services/auth.py
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from app.config.settings import settings
from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.auth.otp import generate_otp, save_otp, verify_otp
from core.errors import ValidationError, InternalServerError, NotFoundError
from domain.schemas.session import SessionCreate

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: Database):
        self.db = db

    def register_vendor(self, vendor_data: Dict[str, Any]) -> Dict[str, str]:
        """Register a new vendor and initiate OTP verification."""
        try:
            required_fields = ["name", "owner_name", "owner_phone", "address", "location", "city", "province", "business_category_ids"]
            for field in required_fields:
                if not vendor_data.get(field):
                    raise ValidationError(f"{field} is required")
            if not vendor_data["owner_phone"].startswith("+"):
                raise ValidationError("Invalid phone number format")
            if self.db.vendors.find_one({"owner_phone": vendor_data["owner_phone"]}):
                raise ValidationError("Phone number already registered")
            for cat_id in vendor_data["business_category_ids"]:
                if not ObjectId.is_valid(cat_id):
                    raise ValidationError(f"Invalid business category ID format: {cat_id}")
                if not self.db.business_categories.find_one({"_id": ObjectId(cat_id)}):
                    raise ValidationError(f"Business category {cat_id} not found")

            full_vendor_data = {
                "username": None,
                "name": vendor_data["name"],
                "owner_name": vendor_data["owner_name"],
                "owner_phone": vendor_data["owner_phone"],
                "phone": None,
                "email": None,
                "password": None,
                "address": vendor_data["address"],
                "location": vendor_data["location"],
                "city": vendor_data["city"],
                "province": vendor_data["province"],
                "business_category_ids": vendor_data["business_category_ids"],
                "roles": ["vendor"],
                "status": "pending",
                "bio": None,
                "avatar_urls": [],
                "products": [],
                "stories": [],
                "wallet_balance": 0.0,
                "followers": [],
                "following_vendor_ids": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            result = self.db.vendors.insert_one(full_vendor_data)
            vendor_id = str(result.inserted_id)

            admins = self.db.users.find({"roles": "admin"})
            for admin in admins:
                self.db.notifications.insert_one({
                    "user_id": str(admin["_id"]),
                    "vendor_id": None,
                    "type": "vendor_registration",
                    "message": f"New vendor {vendor_data['name']} (ID: {vendor_id}) awaiting approval",
                    "status": "unread",
                    "related_id": vendor_id,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })

            otp = generate_otp()
            save_otp(self.db, vendor_data["owner_phone"], otp)
            logger.info(f"OTP sent to {vendor_data['owner_phone']}: {otp}")
            print(f"DEBUG: OTP for {vendor_data['owner_phone']} is {otp}")
            return {"message": "Registration started, OTP sent", "vendor_id": vendor_id}
        except ValidationError as ve:
            logger.error(f"Validation error: {ve.detail}")
            raise ve
        except DuplicateKeyError:
            logger.error("Duplicate key error")
            raise ValidationError("Duplicate entry detected")
        except OperationFailure as of:
            logger.error(f"Database error: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to register vendor: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to register vendor: {str(e)}")

    def verify_registration(self, phone: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and complete registration."""
        try:
            if not verify_otp(self.db, phone, otp):
                raise ValidationError("Invalid OTP")

            user = self.db.users.find_one({"phone": phone})
            entity_type = "user"
            if not user:
                user = self.db.vendors.find_one({"owner_phone": phone})
                entity_type = "vendor"
            if not user:
                raise ValidationError("Entity not found")

            response = {
                "message": "Registration completed",
                "id": str(user["_id"]),
                "status": user["status"],
                "roles": user["roles"]
            }

            if user["status"] == "active":
                access_token = create_access_token(str(user["_id"]), user["roles"])
                refresh_token = create_refresh_token(str(user["_id"]), user["roles"])
                session_data = {
                    "user_id": str(user["_id"]),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "status": "active",
                    "device_info": "Unknown",
                    "expires_at": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                session_id = self.db.sessions.insert_one(session_data).inserted_id
                logger.info(f"Session created for {entity_type} {user['_id']}: {session_id}")
                response.update({"access_token": access_token, "refresh_token": refresh_token})

            logger.info(f"{entity_type.capitalize()} {user['_id']} completed registration")
            return response
        except ValidationError as ve:
            logger.error(f"Validation error: {ve.detail}")
            raise ve
        except OperationFailure as of:
            logger.error(f"Database error: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to verify registration: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to verify registration: {str(e)}")

    def register_user(self, phone: str, requested_role: str = "user") -> Dict[str, str]:
        """Register a new user and initiate OTP verification."""
        try:
            if not phone or not phone.startswith("+"):
                raise ValidationError("Invalid phone number format")
            if self.db.users.find_one({"phone": phone}):
                raise ValidationError("Phone number already registered")
            if requested_role not in ["user"]:
                raise ValidationError("Invalid role. Only 'user' allowed")

            user_data = {
                "phone": phone,
                "first_name": None,
                "last_name": None,
                "roles": [requested_role],
                "status": "active",
                "avatar_urls": [],
                "following_vendor_ids": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            result = self.db.users.insert_one(user_data)
            user_id = str(result.inserted_id)

            otp = generate_otp()
            save_otp(self.db, phone, otp)
            logger.info(f"User registration started for phone: {phone}, user_id: {user_id}, OTP: {otp}")
            print(f"DEBUG: OTP for {phone} is {otp}")
            return {"message": "Registration started, OTP sent", "user_id": user_id}
        except ValidationError as ve:
            logger.error(f"Validation error: {ve.detail}")
            raise ve
        except DuplicateKeyError:
            logger.error("Duplicate key error")
            raise ValidationError("Duplicate entry detected")
        except OperationFailure as of:
            logger.error(f"Database error: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to register user: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to register user: {str(e)}")

    def login(self, phone: str) -> Dict[str, str]:
        """Initiate login by sending OTP."""
        try:
            if not phone or not phone.startswith("+"):
                raise ValidationError("Invalid phone number format")
            user = self.db.users.find_one({"phone": phone})
            entity_type = "user"
            if not user:
                user = self.db.vendors.find_one({"owner_phone": phone})
                entity_type = "vendor"
            if not user:
                raise ValidationError("Phone number not registered")
            if user["status"] != "active":
                raise ValidationError("Account not active")

            phone_field = "phone" if entity_type == "user" else "owner_phone"
            otp = generate_otp()
            save_otp(self.db, phone, otp)
            logger.info(f"OTP sent to {phone} for login: {otp}")
            print(f"DEBUG: OTP for {phone} is {otp}")
            return {"message": "OTP sent for login", "id": str(user["_id"])}
        except ValidationError as ve:
            logger.error(f"Validation error: {ve.detail}")
            raise ve
        except OperationFailure as of:
            logger.error(f"Database error: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to send OTP for login: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to send OTP for login: {str(e)}")

    def verify_login(self, phone: str) -> Dict[str, Any]:
        """Verify OTP and complete login with session creation in a transaction."""
        try:
            user = self.db.users.find_one({"phone": phone})
            entity_type = "user"
            if not user:
                user = self.db.vendors.find_one({"owner_phone": phone})
                entity_type = "vendor"
            if not user or user["status"] != "active":
                raise NotFoundError("Entity not found or not active")

            access_token = create_access_token(str(user["_id"]), user["roles"])
            refresh_token = create_refresh_token(str(user["_id"]), user["roles"])
            session_data = SessionCreate(
                user_id=str(user["_id"]),
                access_token=access_token,
                refresh_token=refresh_token,
                device_info="Unknown",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            ).model_dump()
            session_data["status"] = "active"
            session_data["created_at"] = datetime.now(timezone.utc)
            session_data["updated_at"] = datetime.now(timezone.utc)

            with self.db.client.start_session() as session:
                with session.start_transaction():
                    session_id = self.db.sessions.insert_one(session_data, session=session).inserted_id
                    logger.info(f"Session created for {entity_type} {user['_id']}: {session_id}")

            logger.info(f"Login verified for {entity_type} {user['_id']}")
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "id": str(user["_id"]),
                "roles": user["roles"]
            }
        except NotFoundError as ne:
            logger.error(f"Not found error: {ne.detail}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database error: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to verify login: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to verify login: {str(e)}")

    def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """Refresh an access token using a refresh token with transaction."""
        try:
            payload = decode_token(refresh_token, settings.REFRESH_SECRET_KEY)
            user_id = payload["sub"]
            if not user_id or not ObjectId.is_valid(user_id):
                raise ValidationError("Invalid or missing user_id in refresh token")

            session = self.db.sessions.find_one({"user_id": user_id, "refresh_token": refresh_token})
            if not session or session["status"] != "active":
                raise ValidationError("Invalid or expired refresh token")

            user = self.db.users.find_one({"_id": ObjectId(user_id)})
            entity_type = "user"
            if not user:
                user = self.db.vendors.find_one({"_id": ObjectId(user_id)})
                entity_type = "vendor"
            if not user:
                raise NotFoundError("Entity not found")

            new_access_token = create_access_token(user_id, user["roles"])
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

            with self.db.client.start_session() as session:
                with session.start_transaction():
                    updated = self.db.sessions.update_one(
                        {"user_id": user_id, "refresh_token": refresh_token},
                        {"$set": {"access_token": new_access_token, "expires_at": expires_at, "updated_at": datetime.now(timezone.utc)}},
                        session=session
                    )
                    if updated.matched_count == 0:
                        raise InternalServerError("Failed to update session")

            logger.info(f"Token refreshed for {entity_type} {user_id}")
            return {"access_token": new_access_token, "refresh_token": refresh_token}
        except ValidationError as ve:
            logger.error(f"Validation error: {ve.detail}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error: {ne.detail}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database error: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to refresh token: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to refresh token: {str(e)}")
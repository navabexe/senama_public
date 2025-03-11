# services/auth.py
import logging
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from app.config.settings import settings
from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.auth.otp import generate_otp, save_otp, verify_otp
from core.errors import ValidationError, InternalServerError, NotFoundError
from core.utils.db import DBHelper

logger = logging.getLogger(__name__)


def register_vendor(db: Database, vendor_data: dict) -> dict:
    """Register a new vendor and initiate OTP verification.

    Args:
        db (Database): MongoDB database instance.
        vendor_data (dict): Vendor registration data.

    Returns:
        dict: Registration response with vendor ID and message.

    Raises:
        ValidationError: If required fields are missing or invalid.
        InternalServerError: For unexpected errors.
    """
    db_helper = DBHelper()
    try:
        required_fields = ["name", "owner_name", "owner_phone", "address", "location", "city", "province",
                           "business_category_ids"]
        for field in required_fields:
            if not vendor_data.get(field):
                raise ValidationError(f"{field} is required")
        if not vendor_data["owner_phone"].startswith("+"):
            raise ValidationError("Invalid phone number format")
        if db_helper.find_one("vendors", {"owner_phone": vendor_data["owner_phone"]}):
            raise ValidationError("Phone number already registered")
        for cat_id in vendor_data["business_category_ids"]:
            if not ObjectId.is_valid(cat_id):
                raise ValidationError(f"Invalid business category ID format: {cat_id}")
            if not db_helper.find_one("business_categories", {"_id": ObjectId(cat_id)}):
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
        vendor_id = db_helper.insert_one("vendors", full_vendor_data)

        admins = db_helper.get_collection("users").find({"roles": "admin"})
        for admin in admins:
            db_helper.insert_one("notifications", {
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
        save_otp(db, vendor_data["owner_phone"], otp)
        logger.info(f"OTP sent to {vendor_data['owner_phone']} for registration: {otp}")
        print(f"DEBUG: OTP for {vendor_data['owner_phone']} is {otp}")
        return {"message": "Registration started, OTP sent", "vendor_id": vendor_id}
    except ValidationError as ve:
        logger.error(f"Validation error in register_vendor: {ve.detail}")
        raise ve
    except DuplicateKeyError as dke:
        logger.error(f"Duplicate key error in register_vendor: {str(dke)}")
        raise ValidationError("Duplicate entry detected")
    except OperationFailure as of:
        logger.error(f"Database operation failed in register_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to register vendor: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in register_vendor: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to register vendor: {str(e)}")


def verify_registration(db: Database, phone: str, otp: str) -> dict:
    """Verify OTP and complete registration.

    Args:
        db (Database): MongoDB database instance.
        phone (str): Phone number to verify.
        otp (str): OTP code to validate.

    Returns:
        dict: Verification response with entity details and tokens if active.

    Raises:
        ValidationError: If OTP is invalid or entity not found.
        InternalServerError: For unexpected errors.
    """
    db_helper = DBHelper()
    try:
        if not verify_otp(db, phone, otp):
            raise ValidationError("Invalid OTP")

        user = db_helper.find_one("users", {"phone": phone})
        entity_type = "user"
        if not user:
            user = db_helper.find_one("vendors", {"owner_phone": phone})
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
            session_id = db_helper.insert_one("sessions", session_data)
            logger.info(f"Session created for {entity_type} {user['_id']} with session_id: {session_id}")
            response.update({"access_token": access_token, "refresh_token": refresh_token})

        logger.info(f"{entity_type.capitalize()} {user['_id']} completed registration with role {user['roles']}")
        return response
    except ValidationError as ve:
        logger.error(f"Validation error in verify_registration: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in verify_registration: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to verify registration: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in verify_registration: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to verify registration: {str(e)}")


def login(db: Database, phone: str) -> dict:
    """Initiate login by sending OTP.

    Args:
        db (Database): MongoDB database instance.
        phone (str): Phone number to log in.

    Returns:
        dict: Login response with entity ID and message.

    Raises:
        ValidationError: If phone number is invalid or not registered.
        InternalServerError: For unexpected errors.
    """
    db_helper = DBHelper()
    try:
        if not phone or not phone.startswith("+"):
            raise ValidationError("Invalid phone number")
        user = db_helper.find_one("users", {"phone": phone})
        entity_type = "user"
        if not user:
            user = db_helper.find_one("vendors", {"owner_phone": phone})
            entity_type = "vendor"
        if not user:
            raise ValidationError("Phone number not registered")
        if user["status"] != "active":
            raise ValidationError("Account not active")

        phone_field = "phone" if entity_type == "user" else "owner_phone"
        otp = generate_otp()
        save_otp(db, phone, otp)
        logger.info(f"OTP sent to {phone} for login: {otp}")
        print(f"DEBUG: OTP for {phone} is {otp}")
        return {"message": "OTP sent for login", "id": str(user["_id"])}
    except ValidationError as ve:
        logger.error(f"Validation error in login: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in login: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to send OTP for login: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to send OTP for login: {str(e)}")


def register_user(db: Database, phone: str, requested_role: str) -> dict:
    """Register a new user and initiate OTP verification.

    Args:
        db (Database): MongoDB database instance.
        phone (str): Phone number of the user.
        requested_role (str): Role requested by the user.

    Returns:
        dict: Registration response with user ID and message.

    Raises:
        ValidationError: If phone or role is invalid.
        InternalServerError: For unexpected errors.
    """
    db_helper = DBHelper()
    logger.debug(f"Starting user registration for phone: {phone}, role: {requested_role}")
    try:
        if not phone or not phone.startswith("+"):
            raise ValidationError("Invalid phone number")
        if db_helper.find_one("users", {"phone": phone}):
            raise ValidationError("Phone number already registered")
        if requested_role not in ["user"]:
            raise ValidationError("Invalid role. Only 'user' is allowed here")

        user_data = {
            "phone": phone,
            "first_name": None,
            "last_name": None,
            "password": None,
            "roles": [requested_role],
            "status": "active",
            "otp": None,
            "otp_expires_at": None,
            "bio": None,
            "avatar_urls": [],
            "phones": [phone],
            "birthdate": None,
            "gender": None,
            "languages": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "following_vendor_ids": []
        }
        user_id = db_helper.insert_one("users", user_data)
        otp = generate_otp()
        save_otp(db, phone, otp)
        logger.info(f"User registration started for phone: {phone}, user_id: {user_id}, OTP: {otp}")
        print(f"DEBUG: OTP for {phone} is {otp}")
        return {"message": "Registration started, OTP sent", "user_id": user_id}
    except ValidationError as ve:
        logger.error(f"Validation error in register_user: {ve.detail}, phone: {phone}")
        raise ve
    except DuplicateKeyError as dke:
        logger.error(f"Duplicate key error in register_user: {str(dke)}")
        raise ValidationError("Duplicate entry detected")
    except OperationFailure as of:
        logger.error(f"Database operation failed in register_user: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to register user: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in register_user: {str(e)}, phone: {phone}", exc_info=True)
        raise InternalServerError(f"Failed to register user: {str(e)}")


def verify_login(db: Database, phone: str, otp: str) -> dict:
    """Verify OTP and complete login.

    Args:
        db (Database): MongoDB database instance.
        phone (str): Phone number to verify.
        otp (str): OTP code to validate.

    Returns:
        dict: Login response with tokens and entity details.

    Raises:
        ValidationError: If OTP is invalid or entity not found.
        InternalServerError: For unexpected errors.
    """
    db_helper = DBHelper()
    logger.debug(f"Verifying login for phone: {phone}, OTP: {otp}")
    try:
        if not verify_otp(db, phone, otp):
            raise ValidationError("Invalid OTP")

        user = db_helper.find_one("users", {"phone": phone})
        entity_type = "user"
        if not user:
            user = db_helper.find_one("vendors", {"owner_phone": phone})
            entity_type = "vendor"
        if not user or user["status"] != "active":
            raise ValidationError("Entity not found or not active")

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
        session_id = db_helper.insert_one("sessions", session_data)
        logger.info(
            f"Login verified for {entity_type} - ID: {user['_id']}, session_id: {session_id}, roles: {user['roles']}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "id": str(user["_id"]),
            "roles": user["roles"]
        }
    except ValidationError as ve:
        logger.error(f"Validation error in verify_login: {ve.detail}, phone: {phone}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in verify_login: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to verify login: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in verify_login: {str(e)}, phone: {phone}", exc_info=True)
        raise InternalServerError(f"Failed to verify login: {str(e)}")


def refresh_token(db: Database, refresh_token: str) -> dict:
    """Refresh an access token using a refresh token.

    Args:
        db (Database): MongoDB database instance.
        refresh_token (str): Refresh token to validate.

    Returns:
        dict: New access token and existing refresh token.

    Raises:
        ValidationError: If token is invalid or expired.
        InternalServerError: For unexpected errors.
    """
    db_helper = DBHelper()
    logger.debug(f"Refreshing token with refresh_token: {refresh_token[:10]}...")
    try:
        payload = decode_token(refresh_token, settings.REFRESH_SECRET_KEY)
        user_id = payload.get("sub")
        if not user_id or not ObjectId.is_valid(user_id):
            raise ValidationError("Invalid or missing user_id in refresh token payload")

        session = db_helper.find_one("sessions", {"user_id": user_id, "refresh_token": refresh_token})
        if not session or session["status"] != "active":
            raise ValidationError("Invalid or expired refresh token")

        user = db_helper.find_one("users", {"_id": ObjectId(user_id)})
        entity_type = "user"
        if not user:
            user = db_helper.find_one("vendors", {"_id": ObjectId(user_id)})
            entity_type = "vendor"
        if not user:
            raise NotFoundError("Entity not found")

        new_access_token = create_access_token(user_id, user["roles"])
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        updated = db_helper.update_one(
            "sessions",
            {"user_id": user_id, "refresh_token": refresh_token},
            {"$set": {"access_token": new_access_token, "expires_at": expires_at,
                      "updated_at": datetime.now(timezone.utc)}}
        )
        if not updated:
            raise InternalServerError("Failed to update session with new access token")

        logger.info(f"Token refreshed for {entity_type} - ID: {user_id}, new_expires_at: {expires_at}")
        return {"access_token": new_access_token, "refresh_token": refresh_token}
    except ValidationError as ve:
        logger.error(f"Validation error in refresh_token: {ve.detail}, token: {refresh_token[:10]}...")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in refresh_token: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in refresh_token: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to refresh token: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in refresh_token: {str(e)}, token: {refresh_token[:10]}...", exc_info=True)
        raise InternalServerError(f"Failed to refresh token: {str(e)}")

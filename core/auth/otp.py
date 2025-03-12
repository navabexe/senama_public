# core/auth/otp.py
import logging
import os
import random
from datetime import datetime, timezone, timedelta

from pymongo.database import Database
from pymongo.errors import OperationFailure

from core.errors import ValidationError, InternalServerError

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    """Generate a 6-digit OTP.

    Returns:
        str: Generated OTP.

    Raises:
        InternalServerError: If OTP generation fails unexpectedly.
    """
    try:
        otp = str(random.randint(100000, 999999))
        if os.getenv("ENV") == "development":
            logger.debug(f"Generated OTP: {otp}")
            logger.info(f"Generated OTP: {otp}")
        else:
            logger.debug("OTP generated (hidden in non-development environment)")
        return otp
    except ValueError as ve:
        logger.error(f"ValueError generating OTP: {str(ve)}", exc_info=True)
        raise InternalServerError(f"Failed to generate OTP: {str(ve)}")
    except Exception as e:
        logger.error(f"Unexpected error generating OTP: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to generate OTP: {str(e)}")


def save_otp(db: Database, phone: str, otp: str) -> None:
    """Save an OTP for a phone number with expiration.

    Args:
        db (Database): MongoDB database instance.
        phone (str): Phone number to associate with the OTP.
        otp (str): OTP to save.

    Raises:
        ValidationError: If input data is invalid.
        InternalServerError: If saving OTP fails due to database issues.
    """
    try:
        if not phone or not isinstance(phone, str):
            raise ValidationError("Phone must be a non-empty string")
        if not otp or not isinstance(otp, str):
            raise ValidationError("OTP must be a non-empty string")

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.otps.update_one(
            {"phone": phone},
            {"$set": {"otp": otp, "expires_at": expires_at}},
            upsert=True
        )
        if os.getenv("ENV") == "development":
            logger.info(f"OTP {otp} saved for {phone}, expires at {expires_at}")
        else:
            logger.info(f"OTP saved for {phone}, expires at {expires_at}")
    except ValidationError as ve:
        logger.error(f"Validation error saving OTP: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed saving OTP: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to save OTP: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error saving OTP: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to save OTP: {str(e)}")


def verify_otp(db: Database, phone: str, otp: str) -> bool:
    """Verify an OTP for a phone number.

    Args:
        db (Database): MongoDB database instance.
        phone (str): Phone number to verify OTP for.
        otp (str): OTP to verify.

    Returns:
        bool: True if OTP is valid, False otherwise.

    Raises:
        ValidationError: If OTP is invalid, expired, or input is malformed.
        InternalServerError: If verification fails due to database issues.
    """
    try:
        if not phone or not isinstance(phone, str):
            raise ValidationError("Phone must be a non-empty string")
        if not otp or not isinstance(otp, str):
            raise ValidationError("OTP must be a non-empty string")

        record = db.otps.find_one({"phone": phone})
        if not record or record["otp"] != otp:
            logger.warning(f"Invalid OTP attempt for {phone}")
            raise ValidationError("Invalid OTP")

        expires_at = record["expires_at"]
        if expires_at < datetime.now(timezone.utc):
            logger.warning(f"Expired OTP attempt for {phone}")
            raise ValidationError("Expired OTP")

        db.otps.delete_one({"phone": phone})
        logger.info(f"OTP verified and removed for {phone}")
        return True
    except ValidationError as ve:
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed verifying OTP: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to verify OTP: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error verifying OTP: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to verify OTP: {str(e)}")

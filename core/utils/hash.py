# core/utils/hash.py
import logging

from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from core.errors import InternalServerError, ValidationError

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The hashed password.

    Raises:
        ValidationError: If the password is invalid or empty.
        InternalServerError: If hashing fails due to unexpected errors.
    """
    try:
        if not password or not isinstance(password, str):
            raise ValidationError("Password must be a non-empty string")
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed
    except ValidationError as ve:
        logger.error(f"Validation error hashing password: {ve.detail}")
        raise ve
    except UnknownHashError as uhe:
        logger.error(f"Unknown hash error during password hashing: {str(uhe)}", exc_info=True)
        raise InternalServerError(f"Failed to hash password: Unknown hash format - {str(uhe)}")
    except PasslibRuntimeError as pre:
        logger.error(f"Runtime error during password hashing: {str(pre)}", exc_info=True)
        raise InternalServerError(f"Failed to hash password: Hashing runtime error - {str(pre)}")
    except Exception as e:
        logger.error(f"Unexpected error hashing password: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to hash password: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the password matches, False otherwise.

    Raises:
        ValidationError: If inputs are invalid or empty.
        InternalServerError: If verification fails due to unexpected errors.
    """
    try:
        if not plain_password or not isinstance(plain_password, str):
            raise ValidationError("Plain password must be a non-empty string")
        if not hashed_password or not isinstance(hashed_password, str):
            raise ValidationError("Hashed password must be a non-empty string")

        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"Password verification result: {is_valid}")
        return is_valid
    except ValidationError as ve:
        logger.error(f"Validation error verifying password: {ve.detail}")
        raise ve
    except UnknownHashError as uhe:
        logger.error(f"Unknown hash error during password verification: {str(uhe)}", exc_info=True)
        raise InternalServerError(f"Failed to verify password: Unknown hash format - {str(uhe)}")
    except PasslibRuntimeError as pre:
        logger.error(f"Runtime error during password verification: {str(pre)}", exc_info=True)
        raise InternalServerError(f"Failed to verify password: Verification runtime error - {str(pre)}")
    except Exception as e:
        logger.error(f"Unexpected error verifying password: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to verify password: {str(e)}")


hashed = hash_password("test123")
print(verify_password("test123", hashed))
print(verify_password("wrong", hashed))

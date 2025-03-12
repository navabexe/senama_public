# core/utils/hash.py
import logging

from passlib.context import CryptContext
from passlib.exc import UnknownHashError, PasslibSecurityError

from core.errors import InternalServerError, ValidationError

logger = logging.getLogger(__name__)

# Configure CryptContext with bcrypt as the primary scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    try:
        if not password or not isinstance(password, str):
            raise ValidationError("Password must be a non-empty string")
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise ve
    except UnknownHashError as uhe:
        logger.error(f"Unknown hash error: {str(uhe)}", exc_info=True)
        raise InternalServerError(f"Failed to hash password: {str(uhe)}")
    except PasslibSecurityError as pre:
        logger.error(f"Runtime error: {str(pre)}", exc_info=True)
        raise InternalServerError(f"Failed to hash password: {str(pre)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to hash password: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        if not plain_password or not isinstance(plain_password, str):
            raise ValidationError("Plain password must be a non-empty string")
        if not hashed_password or not isinstance(hashed_password, str):
            raise ValidationError("Hashed password must be a non-empty string")

        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"Password verification result: {is_valid}")
        return is_valid
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise ve
    except UnknownHashError as uhe:
        logger.error(f"Unknown hash error: {str(uhe)}", exc_info=True)
        raise InternalServerError(f"Failed to verify password: {str(uhe)}")
    except PasslibSecurityError as pre:
        logger.error(f"Runtime error: {str(pre)}", exc_info=True)
        raise InternalServerError(f"Failed to verify password: {str(pre)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to verify password: {str(e)}")


# Test the functions
if __name__ == "__main__":
    try:
        hashed = hash_password("test123")
        print(f"Hashed password: {hashed}")
        print(f"Verify 'test123': {verify_password('test123', hashed)}")  # Should print True
        print(f"Verify 'wrong': {verify_password('wrong', hashed)}")  # Should print False
    except Exception as e:
        print(f"Error during test: {str(e)}")
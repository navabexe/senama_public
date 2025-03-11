# core/auth/jwt.py
import logging
from datetime import datetime, timezone, timedelta

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.config.settings import settings
from core.errors import ValidationError

logger = logging.getLogger(__name__)


def create_access_token(user_id: str, roles: list[str]) -> str:
    """Create an access token for a user.

    Args:
        user_id (str): Unique identifier of the user as a string.
        roles (list[str]): List of roles assigned to the user.

    Returns:
        str: Encoded JWT access token.

    Raises:
        ValidationError: If token creation fails due to invalid input or encoding issues.
    """
    try:
        if not user_id or not isinstance(user_id, str):
            raise ValidationError("user_id must be a non-empty string")
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise ValidationError("roles must be a list of strings")

        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": user_id,
            "roles": roles,
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        }
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        logger.info(f"Access token created for user {user_id}")
        return encoded_jwt
    except ValidationError as ve:
        logger.error(f"Validation error creating access token: {ve.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating access token: {str(e)}", exc_info=True)
        raise ValidationError(f"Failed to create access token: {str(e)}")


def create_refresh_token(user_id: str, roles: list[str]) -> str:
    """Create a refresh token for a user.

    Args:
        user_id (str): Unique identifier of the user as a string.
        roles (list[str]): List of roles assigned to the user.

    Returns:
        str: Encoded JWT refresh token.

    Raises:
        ValidationError: If token creation fails due to invalid input or encoding issues.
    """
    try:
        if not user_id or not isinstance(user_id, str):
            raise ValidationError("user_id must be a non-empty string")
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise ValidationError("roles must be a list of strings")

        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {
            "sub": user_id,
            "roles": roles,
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        }
        encoded_jwt = jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm="HS256")
        logger.info(f"Refresh token created for user {user_id}")
        return encoded_jwt
    except ValidationError as ve:
        logger.error(f"Validation error creating refresh token: {ve.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating refresh token: {str(e)}", exc_info=True)
        raise ValidationError(f"Failed to create refresh token: {str(e)}")


def decode_token(token: str, secret_key: str) -> dict:
    """Decode a JWT token and return its payload.

    Args:
        token (str): JWT token to decode.
        secret_key (str): Secret key used for decoding.

    Returns:
        dict: Decoded token payload.

    Raises:
        ValidationError: If token is expired, invalid, or decoding fails.
    """
    try:
        if not token or not isinstance(token, str):
            raise ValidationError("Token must be a non-empty string")
        if not secret_key or not isinstance(secret_key, str):
            raise ValidationError("Secret key must be a non-empty string")

        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        logger.debug(f"Token decoded successfully for user: {payload.get('sub')}")
        return payload
    except ExpiredSignatureError:
        logger.error("Token has expired")
        raise ValidationError("Token has expired")
    except InvalidTokenError:
        logger.error("Invalid token format or signature")
        raise ValidationError("Invalid token")
    except ValidationError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {str(e)}", exc_info=True)
        raise ValidationError(f"Failed to decode token: {str(e)}")

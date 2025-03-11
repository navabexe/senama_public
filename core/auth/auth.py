# core/auth/auth.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, Header
from jwt.exceptions import PyJWTError
from pymongo.database import Database
from pymongo.errors import OperationFailure
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.config.settings import settings
from core.utils.db import DBHelper
from .jwt import decode_token

logger = logging.getLogger(__name__)


def get_current_user(token: str, db: Database) -> dict:
    """Retrieve the current user based on the provided token.

    Args:
        token (str): JWT token from the Authorization header.
        db (Database): MongoDB database instance.

    Returns:
        dict: User or vendor data from the database.

    Raises:
        HTTPException: If credentials are invalid, session is expired, or database errors occur.
    """
    db_helper = DBHelper()
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, settings.SECRET_KEY)
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("No user_id in token payload")
            raise credentials_exception

        if not ObjectId.is_valid(user_id):
            logger.error(f"Invalid user_id format: {user_id}")
            raise credentials_exception

        user = db_helper.find_one("users", {"_id": ObjectId(user_id)})
        if user is None:
            user = db_helper.find_one("vendors", {"_id": ObjectId(user_id)})
        if user is None:
            logger.error(f"No user or vendor found for ID: {user_id}")
            raise credentials_exception

        session_query = {"user_id": user_id, "access_token": token}
        logger.debug(f"Searching session with query: {session_query}")
        session = db_helper.find_one("sessions", session_query)
        if not session:
            logger.error(f"No session found for user_id: {user_id}, token: {token}")
            raise credentials_exception
        if session["status"] != "active":
            logger.error(f"Session status is not active for user_id: {user_id}: {session['status']}")
            raise credentials_exception

        expires_at = session["expires_at"]
        if expires_at < datetime.now(timezone.utc):
            logger.error(f"Session expired for user_id: {user_id}, expires_at: {expires_at}")
            raise credentials_exception

        logger.info(f"User validated: {user_id}")
        return user

    except PyJWTError as je:
        logger.error(f"JWT decoding error: {str(je)}", exc_info=True)
        raise credentials_exception
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Database error during authentication: {str(of)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}", exc_info=True)
        raise credentials_exception


def ensure_role(user: dict, required_role: str) -> None:
    """Ensure the user has the required role.

    Args:
        user (dict): User data from the database.
        required_role (str): Required role for the operation.

    Raises:
        HTTPException: If user does not have the required role.
    """
    if required_role not in user.get("roles", []):
        logger.error(f"User {user.get('_id')} does not have required role: {required_role}")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {required_role} role required",
        )
    logger.debug(f"Role {required_role} verified for user {user.get('_id')}")


async def get_token(authorization: str = Header(...)) -> str:
    """Extract the token from the Authorization header.

    Args:
        authorization (str): Authorization header value.

    Returns:
        str: Extracted token.

    Raises:
        HTTPException: If header is invalid or malformed.
    """
    if not authorization or not authorization.startswith("Bearer "):
        logger.error(f"Invalid authorization header: {authorization}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        token = authorization.split(" ")[1]
        if not token:
            logger.error("Empty token in authorization header")
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Empty token provided",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token
    except IndexError:
        logger.error(f"Malformed authorization header: {authorization}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Malformed authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

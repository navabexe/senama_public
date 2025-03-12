# services/sessions.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.session import Session
from domain.schemas.session import SessionCreate, SessionUpdate

logger = logging.getLogger(__name__)

def create_session(db: Database, user_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new session for a user or vendor with atomic check to prevent duplicates.

    Args:
        db (Database): MongoDB database instance.
        user_id (str): ID of the user or vendor creating the session.
        session_data (Dict[str, Any]): Data for the session including access_token and expires_at.

    Returns:
        Dict[str, str]: Dictionary containing the created session ID.

    Raises:
        ValidationError: If required fields are missing, invalid, or session already exists.
        NotFoundError: If user or vendor is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(user_id, "user_id")
        session_create = SessionCreate(**session_data)  # اعتبارسنجی با Pydantic
        session_data_validated = session_create.model_dump()

        user = db.users.find_one({"_id": ObjectId(user_id)})
        vendor = db.vendors.find_one({"_id": ObjectId(user_id)})
        if not user and not vendor:
            raise NotFoundError(f"User or vendor with ID {user_id} not found")

        session_data_validated["user_id"] = user_id
        session = Session(**session_data_validated)

        with db.client.start_session() as session_db:
            with session_db.start_transaction():
                # بررسی اتمی برای جلوگیری از سشن تکراری
                existing_session = db.sessions.find_one({"access_token": session_data_validated["access_token"]}, session=session_db)
                if existing_session:
                    raise ValidationError(f"Session with access token {session_data_validated['access_token']} already exists")

                result = db.sessions.insert_one(session.model_dump(exclude={"id"}), session=session_db)
                session_id = str(result.inserted_id)

        logger.info(f"Session created with ID: {session_id} for user: {user_id}, token: {session_data_validated['access_token']}")
        return {"id": session_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_session: {ve.detail}, input: {session_data}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_session: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_session: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create session: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_session: {str(e)}, input: {session_data}", exc_info=True)
        raise InternalServerError(f"Failed to create session: {str(e)}")

def get_session(db: Database, session_id: str, user_id: str) -> Session:
    """Retrieve a session by its ID.

    Args:
        db (Database): MongoDB database instance.
        session_id (str): ID of the session to retrieve.
        user_id (str): ID of the user or vendor requesting the session.

    Returns:
        Session: The requested session object.

    Raises:
        ValidationError: If session_id or user_id is invalid.
        NotFoundError: If session is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(session_id, "session_id")
        validate_object_id(user_id, "user_id")

        session = db.sessions.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise NotFoundError(f"Session with ID {session_id} not found")
        if session["user_id"] != user_id:
            raise UnauthorizedError("You can only view your own sessions")

        now = datetime.now(timezone.utc)
        if session["expires_at"] < now and session["status"] != "expired":
            db.sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"status": "expired", "updated_at": now}})
            session["status"] = "expired"
            logger.debug(f"Session {session_id} marked as expired")

        logger.info(f"Session retrieved: {session_id} for user: {user_id}")
        return Session(**session)
    except ValidationError as ve:
        logger.error(f"Validation error in get_session: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_session: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_session: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_session: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get session: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_session: {str(e)}, session_id: {session_id}", exc_info=True)
        raise InternalServerError(f"Failed to get session: {str(e)}")

def get_sessions_by_user(db: Database, user_id: str) -> List[Session]:
    """Retrieve all sessions for a specific user or vendor.

    Args:
        db (Database): MongoDB database instance.
        user_id (str): ID of the user or vendor to retrieve sessions for.

    Returns:
        List[Session]: List of session objects.

    Raises:
        ValidationError: If user_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(user_id, "user_id")

        sessions = list(db.sessions.find({"user_id": user_id}))
        if not sessions:
            logger.debug(f"No sessions found for user_id: {user_id}")
            return []

        now = datetime.now(timezone.utc)
        for session in sessions:
            if session["expires_at"] < now and session["status"] != "expired":
                db.sessions.update_one({"_id": session["_id"]}, {"$set": {"status": "expired", "updated_at": now}})
                session["status"] = "expired"
                logger.debug(f"Session {session['_id']} marked as expired during retrieval")

        logger.info(f"Retrieved {len(sessions)} sessions for user_id: {user_id}")
        return [Session(**session) for session in sessions]
    except ValidationError as ve:
        logger.error(f"Validation error in get_sessions_by_user: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_sessions_by_user: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get sessions: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_sessions_by_user: {str(e)}, user_id: {user_id}", exc_info=True)
        raise InternalServerError(f"Failed to get sessions: {str(e)}")

def update_session(db: Database, session_id: str, user_id: str, update_data: Dict[str, Any]) -> Session:
    """Update an existing session.

    Args:
        db (Database): MongoDB database instance.
        session_id (str): ID of the session to update.
        user_id (str): ID of the user or vendor updating the session.
        update_data (Dict[str, Any]): Data to update in the session (e.g., status, expires_at).

    Returns:
        Session: The updated session object.

    Raises:
        ValidationError: If session_id, user_id, or status is invalid.
        NotFoundError: If session is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(session_id, "session_id")
        validate_object_id(user_id, "user_id")
        session_update = SessionUpdate(**update_data)  # اعتبارسنجی با Pydantic
        update_data_validated = session_update.model_dump(exclude_unset=True)

        session = db.sessions.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise NotFoundError(f"Session with ID {session_id} not found")
        if session["user_id"] != user_id:
            raise UnauthorizedError("You can only update your own sessions")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)
        updated = db.sessions.update_one({"_id": ObjectId(session_id)}, {"$set": update_data_validated})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update session {session_id}")

        updated_session = db.sessions.find_one({"_id": ObjectId(session_id)})
        logger.info(f"Session updated: {session_id}, changes: {update_data_validated}")
        return Session(**updated_session)
    except ValidationError as ve:
        logger.error(f"Validation error in update_session: {ve.detail}, input: {update_data}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_session: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_session: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_session: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update session: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_session: {str(e)}, session_id: {session_id}", exc_info=True)
        raise InternalServerError(f"Failed to update session: {str(e)}")

def revoke_session(db: Database, session_id: str, user_id: str) -> Dict[str, str]:
    """Revoke a session (alternative to delete).

    Args:
        db (Database): MongoDB database instance.
        session_id (str): ID of the session to revoke.
        user_id (str): ID of the user or vendor revoking the session.

    Returns:
        Dict[str, str]: Confirmation message of revocation.

    Raises:
        ValidationError: If session_id or user_id is invalid.
        NotFoundError: If session is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(session_id, "session_id")
        validate_object_id(user_id, "user_id")

        session = db.sessions.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise NotFoundError(f"Session with ID {session_id} not found")
        if session["user_id"] != user_id:
            raise UnauthorizedError("You can only revoke your own sessions")

        db.sessions.update_one({"_id": ObjectId(session_id)},
                               {"$set": {"status": "revoked", "updated_at": datetime.now(timezone.utc)}})
        logger.info(f"Session revoked: {session_id} by user: {user_id}")
        return {"message": f"Session {session_id} revoked successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in revoke_session: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in revoke_session: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in revoke_session: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in revoke_session: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to revoke session: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in revoke_session: {str(e)}, session_id: {session_id}", exc_info=True)
        raise InternalServerError(f"Failed to revoke session: {str(e)}")

def delete_session(db: Database, session_id: str, user_id: str) -> Dict[str, str]:
    """Delete a session.

    Args:
        db (Database): MongoDB database instance.
        session_id (str): ID of the session to delete.
        user_id (str): ID of the user or vendor deleting the session.

    Returns:
        Dict[str, str]: Confirmation message of deletion.

    Raises:
        ValidationError: If session_id or user_id is invalid.
        NotFoundError: If session is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(session_id, "session_id")
        validate_object_id(user_id, "user_id")

        session = db.sessions.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise NotFoundError(f"Session with ID {session_id} not found")
        if session["user_id"] != user_id:
            raise UnauthorizedError("You can only delete your own sessions")

        db.sessions.delete_one({"_id": ObjectId(session_id)})
        logger.info(f"Session deleted: {session_id} by user: {user_id}")
        return {"message": f"Session {session_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_session: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_session: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_session: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_session: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete session: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_session: {str(e)}, session_id: {session_id}", exc_info=True)
        raise InternalServerError(f"Failed to delete session: {str(e)}")

def cleanup_expired_sessions(db: Database) -> Dict[str, str]:
    """Clean up expired sessions by updating their status.

    Args:
        db (Database): MongoDB database instance.

    Returns:
        Dict[str, str]: Confirmation message with count of cleaned sessions.

    Raises:
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        now = datetime.now(timezone.utc)
        expired_sessions = db.sessions.find({"expires_at": {"$lt": now}, "status": {"$ne": "expired"}})
        count = 0
        for session in expired_sessions:
            updated = db.sessions.update_one(
                {"_id": session["_id"]},
                {"$set": {"status": "expired", "updated_at": now}}
            )
            if updated.matched_count > 0:
                count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        else:
            logger.debug("No expired sessions found to clean up")
        return {"message": f"Cleaned up {count} expired sessions"}
    except OperationFailure as of:
        logger.error(f"Database operation failed in cleanup_expired_sessions: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to clean up expired sessions: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in cleanup_expired_sessions: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to clean up expired sessions: {str(e)}")
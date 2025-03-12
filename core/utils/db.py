# core/utils/db.py
import logging

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, OperationFailure, NetworkTimeout

from core.errors import InternalServerError, ValidationError
from infrastructure.database.client import get_db

logger = logging.getLogger(__name__)


class DBHelper:
    """Utility class for interacting with MongoDB database."""

    def __init__(cls):
        """Initialize DBHelper with a MongoDB connection."""
        try:
            cls.db = get_db()
            logger.info("Database connection established")
        except NetworkTimeout as nt:
            logger.error(f"Network timeout connecting to database: {str(nt)}", exc_info=True)
            raise InternalServerError(f"Database connection timeout: {str(nt)}")
        except OperationFailure as of:
            logger.error(f"Database operation failed during initialization: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to initialize database: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error initializing database: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to initialize database: {str(e)}")

    def get_collection(cls, collection_name: str) -> Database:
        """Get a MongoDB collection by name.

        Args:
            collection_name (str): Name of the collection to access.

        Returns:
            Database: The requested collection object.

        Raises:
            ValidationError: If collection_name is invalid.
            InternalServerError: If accessing the collection fails.
        """
        try:
            if not collection_name or not isinstance(collection_name, str):
                raise ValidationError("Collection name must be a non-empty string")
            collection = cls.db[collection_name]
            logger.debug(f"Accessed collection: {collection_name}")
            return collection
        except ValidationError as ve:
            logger.error(f"Validation error accessing collection: {ve.detail}")
            raise ve
        except OperationFailure as of:
            logger.error(f"Database operation failed accessing collection {collection_name}: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to access collection: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error accessing collection {collection_name}: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to access collection: {str(e)}")

    def insert_one(cls, collection_name: str, document: dict) -> str:
        """Insert a single document into a collection.

        Args:
            collection_name (str): Name of the collection.
            document (dict): Document to insert.

        Returns:
            str: ID of the inserted document as a string.

        Raises:
            ValidationError: If document is invalid or a duplicate exists.
            InternalServerError: If insertion fails due to database issues.
        """
        try:
            if not isinstance(document, dict):
                raise ValidationError("Document must be a dictionary")
            collection = cls.get_collection(collection_name)
            result = collection.insert_one(document)
            inserted_id = str(result.inserted_id)
            logger.info(f"Inserted document into {collection_name} with ID: {inserted_id}")
            return inserted_id
        except ValidationError as ve:
            logger.error(f"Validation error inserting into {collection_name}: {ve.detail}")
            raise ve
        except DuplicateKeyError as dke:
            logger.error(f"Duplicate key error inserting into {collection_name}: {str(dke)}")
            raise ValidationError(f"Duplicate entry detected in {collection_name}")
        except OperationFailure as of:
            logger.error(f"Database operation failed inserting into {collection_name}: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to insert document: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error inserting into {collection_name}: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to insert document: {str(e)}")

    def find_one(cls, collection_name: str, query: dict) -> dict:
        """Find a single document in a collection.

        Args:
            collection_name (str): Name of the collection.
            query (dict): Query to match the document, with '_id' as string if present.

        Returns:
            dict: The found document, or None if not found.

        Raises:
            ValidationError: If query is invalid or contains an invalid '_id'.
            InternalServerError: If finding the document fails due to database issues.
        """
        try:
            if not isinstance(query, dict):
                raise ValidationError("Query must be a dictionary")
            if "_id" in query and not ObjectId.is_valid(query["_id"]):
                raise ValidationError(f"Invalid '_id' format in query: {query['_id']}")
            if "_id" in query:
                query["_id"] = ObjectId(query["_id"])

            collection = cls.get_collection(collection_name)
            result = collection.find_one(query)
            if result is None:
                logger.debug(f"No document found in {collection_name} for query: {query}")
            else:
                logger.debug(f"Found document in {collection_name}")
            return result
        except ValidationError as ve:
            logger.error(f"Validation error finding in {collection_name}: {ve.detail}")
            raise ve
        except OperationFailure as of:
            logger.error(f"Database operation failed finding in {collection_name}: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to find document: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error finding in {collection_name}: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to find document: {str(e)}")

    def update_one(cls, collection_name: str, query: dict, update: dict) -> bool:
        """Update a single document in a collection.

        Args:
            collection_name (str): Name of the collection.
            query (dict): Query to match the document, with '_id' as string if present.
            update (dict): Update data to apply.

        Returns:
            bool: True if a document was updated, False if no match was found.

        Raises:
            ValidationError: If query or update is invalid or contains an invalid '_id'.
            InternalServerError: If updating the document fails due to database issues.
        """
        try:
            if not isinstance(query, dict):
                raise ValidationError("Query must be a dictionary")
            if not isinstance(update, dict):
                raise ValidationError("Update must be a dictionary")
            if "_id" in query and not ObjectId.is_valid(query["_id"]):
                raise ValidationError(f"Invalid '_id' format in query: {query['_id']}")
            if "_id" in query:
                query["_id"] = ObjectId(query["_id"])

            collection = cls.get_collection(collection_name)
            result = collection.update_one(query, {"$set": update})
            if result.matched_count == 0:
                logger.debug(f"No document matched in {collection_name} for query: {query}")
                return False
            logger.info(f"Updated document in {collection_name} for query: {query}")
            return True
        except ValidationError as ve:
            logger.error(f"Validation error updating in {collection_name}: {ve.detail}")
            raise ve
        except OperationFailure as of:
            logger.error(f"Database operation failed updating in {collection_name}: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to update document: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error updating in {collection_name}: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to update document: {str(e)}")

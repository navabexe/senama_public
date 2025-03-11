# infrastructure/database/client.py
import logging

from pymongo import MongoClient

from app.config.settings import settings

logger = logging.getLogger(__name__)


def get_db():
    """Get a MongoDB database client instance."""
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB]
        logger.info(f"Connected to MongoDB database: {settings.MONGO_DB}")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}", exc_info=True)
        raise

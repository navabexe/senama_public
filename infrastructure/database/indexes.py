# infrastructure/database/indexes.py
import logging

from pymongo import ASCENDING

from infrastructure.database.client import get_db

logger = logging.getLogger(__name__)


def create_indexes():
    """Create indexes for MongoDB collections."""
    db = get_db()
    try:
        # Users collection
        db.users.create_index([("phone", ASCENDING)], unique=True)
        db.users.create_index([("status", ASCENDING)])

        # Vendors collection
        db.vendors.create_index([("phone", ASCENDING)], unique=True)
        db.vendors.create_index([("status", ASCENDING)])

        # Products collection
        db.products.create_index([("vendor_id", ASCENDING)])
        db.products.create_index([("category_ids", ASCENDING)])
        db.products.create_index([("status", ASCENDING)])

        # Orders collection
        db.orders.create_index([("user_id", ASCENDING)])
        db.orders.create_index([("vendor_id", ASCENDING)])
        db.orders.create_index([("status", ASCENDING)])

        # Advertisements collection
        db.advertisements.create_index([("vendor_id", ASCENDING)])
        db.advertisements.create_index([("status", ASCENDING)])

        # Stories collection
        db.stories.create_index([("vendor_id", ASCENDING)])
        db.stories.create_index([("status", ASCENDING)])
        db.stories.create_index([("expires_at", ASCENDING)])

        # Transactions collection
        db.transactions.create_index([("vendor_id", ASCENDING)])
        db.transactions.create_index([("status", ASCENDING)])

        # Sessions collection
        db.sessions.create_index([("user_id", ASCENDING)])
        db.sessions.create_index([("status", ASCENDING)])
        db.sessions.create_index([("expires_at", ASCENDING)])

        # Blocked Users collection
        db.blocked_users.create_index([("blocker_id", ASCENDING)])
        db.blocked_users.create_index([("blocked_id", ASCENDING)])

        # Reports collection
        db.reports.create_index([("reporter_id", ASCENDING)])
        db.reports.create_index([("reported_id", ASCENDING)])
        db.reports.create_index([("status", ASCENDING)])

        # Notifications collection
        db.notifications.create_index([("user_id", ASCENDING)])
        db.notifications.create_index([("vendor_id", ASCENDING)])
        db.notifications.create_index([("status", ASCENDING)])

        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create database indexes: {str(e)}", exc_info=True)
        raise

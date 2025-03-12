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

        db.collaborations.create_index(
            [("requester_vendor_id", 1), ("target_vendor_id", 1), ("product_id", 1)],
            unique=True,
            name="unique_collaboration_idx"
        )

        db.notifications.create_index(
            [("user_id", 1), ("vendor_id", 1), ("type", 1), ("related_id", 1)],
            unique=True,
            name="unique_notification_idx",
            partialFilterExpression={"user_id": {"$exists": True}, "vendor_id": {"$exists": True}}
        )

        db.product_categories.create_index(
            [("name", 1)],
            unique=True,
            name="unique_product_category_name_idx"
        )
        db.products.create_index(
            [("vendor_id", 1), ("name", 1)],
            unique=True,
            name="unique_product_vendor_name_idx"
        )
        db.reports.create_index(
            [("reporter_id", 1), ("target_id", 1), ("target_type", 1)],
            unique=True,
            name="unique_report_idx"
        )
        db.sessions.create_index(
            [("access_token", 1)],
            unique=True,
            name="unique_session_access_token_idx"
        )
        db.stories.create_index(
            [("vendor_id", 1), ("media_url", 1)],
            unique=True,
            name="unique_story_vendor_media_idx"
        )
        db.transactions.create_index(
            [("vendor_id", 1), ("created_at", 1)],
            unique=True,
            name="unique_transaction_vendor_time_idx"
        )
        db.uploaded_files.create_index(
            [("file_url", 1)],
            unique=True,
            name="unique_file_url_idx"
        )
        db.users.create_index(
            [("phone", 1)],
            unique=True,
            name="unique_user_phone_idx"
        )
        db.vendors.create_index(
            [("username", 1)],
            unique=True,
            name="unique_vendor_username_idx"
        )
        db.vendors.create_index(
            [("phone", 1)],
            unique=True,
            name="unique_vendor_phone_idx"
        )
        db.vendors.create_index(
            [("username", 1)],
            unique=True,
            name="unique_vendor_username_idx"
        )
        db.vendors.create_index(
            [("phone", 1)],
            unique=True,
            name="unique_vendor_phone_idx"
        )



        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create database indexes: {str(e)}", exc_info=True)
        raise

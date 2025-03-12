# services/admin.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.db import DBHelper
from core.utils.validation import validate_object_id
from domain.entities.vendor import Vendor

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(cls, db: Database):
        """Initialize AdminService with a database instance."""
        cls.db_helper = DBHelper()
        cls.db = db

    def verify_vendor(cls, admin_id: str, vendor_id: str, status: str) -> Vendor:
        """Verify a vendor by setting their status (admin only)."""
        logger.debug(f"Admin {admin_id} attempting to verify vendor {vendor_id} with status: {status}")
        try:
            validate_object_id(admin_id, "admin_id")
            validate_object_id(vendor_id, "vendor_id")

            admin = cls.db_helper.find_one("users", {"_id": ObjectId(admin_id)})
            if not admin or "admin" not in admin["roles"]:
                raise UnauthorizedError("Only admins can verify vendors")

            vendor = cls.db_helper.find_one("vendors", {"_id": ObjectId(vendor_id)})
            if not vendor:
                raise NotFoundError(f"Vendor with ID {vendor_id} not found")

            if status not in ["active", "rejected"]:
                raise ValidationError("Status must be 'active' or 'rejected'")

            update_data = {"status": status, "updated_at": datetime.now(timezone.utc)}
            updated = cls.db_helper.update_one("vendors", {"_id": ObjectId(vendor_id)}, update_data)
            if not updated:
                raise InternalServerError(f"Failed to update vendor {vendor_id}")

            updated_vendor = cls.db_helper.find_one("vendors", {"_id": ObjectId(vendor_id)})
            logger.info(f"Vendor {vendor_id} verified by admin {admin_id} - new status: {status}")
            return Vendor(**updated_vendor)
        except (UnauthorizedError, ValidationError, NotFoundError) as e:
            logger.error(f"Error in verify_vendor: {e.detail}, admin_id: {admin_id}")
            raise e
        except OperationFailure as of:
            logger.error(f"Database operation failed in verify_vendor: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to verify vendor: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in verify_vendor: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to verify vendor: {str(e)}")

    def deactivate_account(cls, admin_id: str, target_id: str, target_type: str) -> Dict[str, str]:
        """Deactivate a user or vendor account (admin only) with transaction."""
        logger.debug(f"Admin {admin_id} attempting to deactivate {target_type} {target_id}")
        try:
            validate_object_id(admin_id, "admin_id")
            validate_object_id(target_id, "target_id")

            admin = cls.db_helper.find_one("users", {"_id": ObjectId(admin_id)})
            if not admin or "admin" not in admin["roles"]:
                raise UnauthorizedError("Only admins can deactivate accounts")

            if target_type not in ["user", "vendor"]:
                raise ValidationError("Target type must be 'user' or 'vendor'")

            collection_name = "users" if target_type == "user" else "vendors"
            target = cls.db_helper.find_one(collection_name, {"_id": ObjectId(target_id)})
            if not target:
                raise NotFoundError(f"{target_type.capitalize()} with ID {target_id} not found")

            update_data = {"status": "deactivated", "updated_at": datetime.now(timezone.utc)}
            with cls.db.client.start_session() as session:
                with session.start_transaction():
                    updated = cls.db_helper.update_one(collection_name, {"_id": ObjectId(target_id)}, update_data, session=session)
                    if not updated:
                        raise InternalServerError(f"Failed to deactivate {target_type} {target_id}")

            logger.info(f"{target_type.capitalize()} {target_id} deactivated by admin {admin_id}")
            return {"message": f"{target_type.capitalize()} {target_id} deactivated successfully"}
        except (UnauthorizedError, ValidationError, NotFoundError) as e:
            logger.error(f"Error in deactivate_account: {e.detail}, admin_id: {admin_id}")
            raise e
        except OperationFailure as of:
            logger.error(f"Database operation failed in deactivate_account: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to deactivate account: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in deactivate_account: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to deactivate account: {str(e)}")

    def delete_account(cls, admin_id: str, target_id: str, target_type: str) -> Dict[str, str]:
        """Delete a user or vendor account (admin only) with transaction."""
        logger.debug(f"Admin {admin_id} attempting to delete {target_type} {target_id}")
        try:
            validate_object_id(admin_id, "admin_id")
            validate_object_id(target_id, "target_id")

            admin = cls.db_helper.find_one("users", {"_id": ObjectId(admin_id)})
            if not admin or "admin" not in admin["roles"]:
                raise UnauthorizedError("Only admins can delete accounts")

            if target_type not in ["user", "vendor"]:
                raise ValidationError("Target type must be 'user' or 'vendor'")

            collection_name = "users" if target_type == "user" else "vendors"
            target = cls.db_helper.find_one(collection_name, {"_id": ObjectId(target_id)})
            if not target:
                raise NotFoundError(f"{target_type.capitalize()} with ID {target_id} not found")

            with cls.db.client.start_session() as session:
                with session.start_transaction():
                    cls.db[collection_name].delete_one({"_id": ObjectId(target_id)}, session=session)

            logger.info(f"{target_type.capitalize()} {target_id} deleted by admin {admin_id}")
            return {"message": f"{target_type.capitalize()} {target_id} deleted successfully"}
        except (UnauthorizedError, ValidationError, NotFoundError) as e:
            logger.error(f"Error in delete_account: {e.detail}, admin_id: {admin_id}")
            raise e
        except OperationFailure as of:
            logger.error(f"Database operation failed in delete_account: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to delete account: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in delete_account: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to delete account: {str(e)}")
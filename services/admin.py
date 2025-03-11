# services/admin.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.db import DBHelper
from domain.entities.vendor import Vendor

logger = logging.getLogger(__name__)  # اصلاح name به __name__


class AdminService:
    def __init__(self, db: Database):  # اصلاح init به __init__
        """Initialize AdminService with a database instance."""
        self.db_helper = DBHelper()
        self.db = db

    def verify_vendor(self, admin_id: str, vendor_id: str, status: str) -> Vendor:
        """Verify a vendor by setting their status (admin only).

        Args:
            admin_id (str): ID of the admin performing the action.
            vendor_id (str): ID of the vendor to verify.
            status (str): Status to set ('active' or 'rejected').

        Returns:
            Vendor: Updated vendor entity.

        Raises:
            UnauthorizedError: If the user is not an admin.
            NotFoundError: If the vendor is not found.
            ValidationError: If the status is invalid.
            InternalServerError: For unexpected errors.
        """
        logger.debug(f"Admin {admin_id} attempting to verify vendor {vendor_id} with status: {status}")
        try:
            if not ObjectId.is_valid(admin_id):
                raise ValidationError(f"Invalid admin_id format: {admin_id}")
            if not ObjectId.is_valid(vendor_id):
                raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

            admin = self.db_helper.find_one("users", {"_id": ObjectId(admin_id)})
            if not admin or "admin" not in admin["roles"]:
                raise UnauthorizedError("Only admins can verify vendors")

            vendor = self.db_helper.find_one("vendors", {"_id": ObjectId(vendor_id)})
            if not vendor:
                raise NotFoundError(f"Vendor with ID {vendor_id} not found")

            if status not in ["active", "rejected"]:
                raise ValidationError("Status must be 'active' or 'rejected'")

            update_data = {"status": status, "updated_at": datetime.now(timezone.utc)}
            updated = self.db_helper.update_one("vendors", {"_id": ObjectId(vendor_id)}, update_data)
            if not updated:
                raise InternalServerError(f"Failed to update vendor {vendor_id}")

            updated_vendor = self.db_helper.find_one("vendors", {"_id": ObjectId(vendor_id)})
            logger.info(f"Vendor {vendor_id} verified by admin {admin_id} - new status: {status}")
            return Vendor(**updated_vendor)
        except UnauthorizedError as ue:
            logger.error(f"Unauthorized error in verify_vendor: {ue.detail}, admin_id: {admin_id}")
            raise ue
        except ValidationError as ve:
            logger.error(f"Validation error in verify_vendor: {ve.detail}, vendor_id: {vendor_id}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error in verify_vendor: {ne.detail}, vendor_id: {vendor_id}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database operation failed in verify_vendor: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to verify vendor: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in verify_vendor: {str(e)}, admin_id: {admin_id}, vendor_id: {vendor_id}",
                         exc_info=True)
            raise InternalServerError(f"Failed to verify vendor: {str(e)}")

    def deactivate_account(self, admin_id: str, target_id: str, target_type: str) -> dict:
        """Deactivate a user or vendor account (admin only).

        Args:
            admin_id (str): ID of the admin performing the action.
            target_id (str): ID of the target account to deactivate.
            target_type (str): Type of the target ('user' or 'vendor').

        Returns:
            dict: Confirmation message.

        Raises:
            UnauthorizedError: If the user is not an admin.
            ValidationError: If the target type is invalid.
            NotFoundError: If the target account is not found.
            InternalServerError: For unexpected errors.
        """
        logger.debug(f"Admin {admin_id} attempting to deactivate {target_type} {target_id}")
        try:
            if not ObjectId.is_valid(admin_id):
                raise ValidationError(f"Invalid admin_id format: {admin_id}")
            if not ObjectId.is_valid(target_id):
                raise ValidationError(f"Invalid target_id format: {target_id}")

            admin = self.db_helper.find_one("users", {"_id": ObjectId(admin_id)})
            if not admin or "admin" not in admin["roles"]:
                raise UnauthorizedError("Only admins can deactivate accounts")

            if target_type not in ["user", "vendor"]:
                raise ValidationError("Target type must be 'user' or 'vendor'")

            collection_name = "users" if target_type == "user" else "vendors"
            target = self.db_helper.find_one(collection_name, {"_id": ObjectId(target_id)})
            if not target:
                raise NotFoundError(f"{target_type.capitalize()} with ID {target_id} not found")

            update_data = {"status": "deactivated", "updated_at": datetime.now(timezone.utc)}
            updated = self.db_helper.update_one(collection_name, {"_id": ObjectId(target_id)}, update_data)
            if not updated:
                raise InternalServerError(f"Failed to deactivate {target_type} {target_id}")

            logger.info(f"{target_type.capitalize()} {target_id} deactivated by admin {admin_id}")
            return {"message": f"{target_type.capitalize()} {target_id} deactivated successfully"}
        except UnauthorizedError as ue:
            logger.error(f"Unauthorized error in deactivate_account: {ue.detail}, admin_id: {admin_id}")
            raise ue
        except ValidationError as ve:
            logger.error(f"Validation error in deactivate_account: {ve.detail}, target_type: {target_type}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error in deactivate_account: {ne.detail}, target_id: {target_id}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database operation failed in deactivate_account: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to deactivate account: {str(of)}")
        except Exception as e:
            logger.error(
                f"Unexpected error in deactivate_account: {str(e)}, admin_id: {admin_id}, target_id: {target_id}",
                exc_info=True)
            raise InternalServerError(f"Failed to deactivate account: {str(e)}")

    def delete_account(self, admin_id: str, target_id: str, target_type: str) -> dict:
        """Delete a user or vendor account (admin only).

        Args:
            admin_id (str): ID of the admin performing the action.
            target_id (str): ID of the target account to delete.
            target_type (str): Type of the target ('user' or 'vendor').

        Returns:
            dict: Confirmation message.

        Raises:
            UnauthorizedError: If the user is not an admin.
            ValidationError: If the target type is invalid.
            NotFoundError: If the target account is not found.
            InternalServerError: For unexpected errors.
        """
        logger.debug(f"Admin {admin_id} attempting to delete {target_type} {target_id}")
        try:
            if not ObjectId.is_valid(admin_id):
                raise ValidationError(f"Invalid admin_id format: {admin_id}")
            if not ObjectId.is_valid(target_id):
                raise ValidationError(f"Invalid target_id format: {target_id}")

            admin = self.db_helper.find_one("users", {"_id": ObjectId(admin_id)})
            if not admin or "admin" not in admin["roles"]:
                raise UnauthorizedError("Only admins can delete accounts")

            if target_type not in ["user", "vendor"]:
                raise ValidationError("Target type must be 'user' or 'vendor'")

            collection_name = "users" if target_type == "user" else "vendors"
            target = self.db_helper.find_one(collection_name, {"_id": ObjectId(target_id)})
            if not target:
                raise NotFoundError(f"{target_type.capitalize()} with ID {target_id} not found")

            self.db[collection_name].delete_one({"_id": ObjectId(target_id)})
            logger.info(f"{target_type.capitalize()} {target_id} deleted by admin {admin_id}")
            return {"message": f"{target_type.capitalize()} {target_id} deleted successfully"}
        except UnauthorizedError as ue:
            logger.error(f"Unauthorized error in delete_account: {ue.detail}, admin_id: {admin_id}")
            raise ue
        except ValidationError as ve:
            logger.error(f"Validation error in delete_account: {ve.detail}, target_type: {target_type}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error in delete_account: {ne.detail}, target_id: {target_id}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database operation failed in delete_account: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to delete account: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in delete_account: {str(e)}, admin_id: {admin_id}, target_id: {target_id}",
                         exc_info=True)
            raise InternalServerError(f"Failed to delete account: {str(e)}")

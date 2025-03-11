# services/vendors.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, InternalServerError, UnauthorizedError
from core.utils.db import DBHelper
from domain.entities.vendor import Vendor

logger = logging.getLogger(__name__)


def create_vendor(db: Database, vendor_data: dict) -> dict:
    """Create a new vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_data (dict): Data for the vendor including username, name, owner_name, phone, etc.

    Returns:
        dict: Dictionary containing the created vendor ID.

    Raises:
        ValidationError: If required fields are missing or invalid.
        NotFoundError: If any business category is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    db_helper = DBHelper()
    try:
        required_fields = ["username", "name", "owner_name", "phone", "business_category_ids", "address", "city",
                           "province", "location"]
        for field in required_fields:
            if not vendor_data.get(field):
                raise ValidationError(f"{field} is required")
        if db_helper.find_one("vendors", {"username": vendor_data["username"]}):
            raise ValidationError("Username already taken")
        if db_helper.find_one("vendors", {"phone": vendor_data["phone"]}):
            raise ValidationError("Phone number already registered")

        category_ids = vendor_data["business_category_ids"]
        if not isinstance(category_ids, list) or not category_ids:
            raise ValidationError("business_category_ids must be a non-empty list")
        for category_id in category_ids:
            if not ObjectId.is_valid(category_id):
                raise ValidationError(f"Invalid category_id format: {category_id}")
            if not db_helper.find_one("business_categories", {"_id": ObjectId(category_id)}):
                raise NotFoundError(f"Business category with ID {category_id} not found")

        vendor = Vendor(**vendor_data)
        vendor_id = db_helper.insert_one("vendors", vendor.model_dump(exclude={"id"}))

        admins = db_helper.get_collection("users").find({"roles": {"$in": ["admin"]}})
        for admin in admins:
            notification_data = {
                "user_id": str(admin["_id"]),
                "vendor_id": None,
                "type": "vendor_verification",
                "message": f"New vendor {vendor_data['username']} (ID: {vendor_id}) awaiting verification",
                "status": "unread",
                "related_id": vendor_id,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            db_helper.insert_one("notifications", notification_data)

        logger.info(f"Vendor created with ID: {vendor_id}")
        return {"id": vendor_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_vendor: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_vendor: {ne.detail}")
        raise ne
    except DuplicateKeyError:
        logger.error("Duplicate vendor detected")
        raise ValidationError("A vendor with this username or phone already exists")
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create vendor: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_vendor: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create vendor: {str(e)}")


def get_vendor(db: Database, vendor_id: str, requester_id: str = None) -> Vendor:
    """Retrieve a vendor by their ID.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve.
        requester_id (str, optional): ID of the user requesting the data, for authorization check.

    Returns:
        Vendor: The requested vendor object.

    Raises:
        ValidationError: If vendor_id format is invalid.
        NotFoundError: If vendor is not found.
        UnauthorizedError: If requester is not authorized (when applicable).
        InternalServerError: For unexpected errors or database failures.
    """
    db_helper = DBHelper()
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor ID format: {vendor_id}")

        vendor = db_helper.find_one("vendors", {"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")

        # اگر requester_id داده شده باشه، بررسی دسترسی
        if requester_id:
            if not ObjectId.is_valid(requester_id):
                raise ValidationError(f"Invalid requester_id format: {requester_id}")
            if requester_id != vendor_id:
                requester = db_helper.find_one("users", {"_id": ObjectId(requester_id)})
                if not requester or "admin" not in requester.get("roles", []):
                    raise UnauthorizedError("You can only view your own profile unless you are an admin")

        logger.info(f"Vendor retrieved: {vendor_id}")
        return Vendor(**vendor)
    except ValidationError as ve:
        logger.error(f"Validation error in get_vendor: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_vendor: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_vendor: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get vendor: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_vendor: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get vendor: {str(e)}")


def update_vendor(db: Database, vendor_id: str, requester_id: str, update_data: dict) -> Vendor:
    """Update an existing vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to update.
        requester_id (str): ID of the user or vendor requesting the update.
        update_data (dict): Data to update in the vendor.

    Returns:
        Vendor: The updated vendor object.

    Raises:
        ValidationError: If vendor_id or requester_id is invalid.
        NotFoundError: If vendor is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    db_helper = DBHelper()
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor ID format: {vendor_id}")
        if not ObjectId.is_valid(requester_id):
            raise ValidationError(f"Invalid requester_id format: {requester_id}")

        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")

        if requester_id != vendor_id:
            requester = db_helper.find_one("users", {"_id": ObjectId(requester_id)})
            if not requester or "admin" not in requester.get("roles", []):
                raise UnauthorizedError("You can only update your own profile unless you are an admin")

        if "business_category_ids" in update_data:
            category_ids = update_data["business_category_ids"]
            if not isinstance(category_ids, list) or not category_ids:
                raise ValidationError("business_category_ids must be a non-empty list")
            for category_id in category_ids:
                if not ObjectId.is_valid(category_id):
                    raise ValidationError(f"Invalid category_id format: {category_id}")
                if not db_helper.find_one("business_categories", {"_id": ObjectId(category_id)}):
                    raise NotFoundError(f"Business category with ID {category_id} not found")

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$set": update_data})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update vendor {vendor_id}")

        updated_vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        logger.info(f"Vendor updated: {vendor_id}")
        return Vendor(**updated_vendor)
    except ValidationError as ve:
        logger.error(f"Validation error in update_vendor: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_vendor: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_vendor: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update vendor: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_vendor: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update vendor: {str(e)}")


def delete_vendor(db: Database, vendor_id: str, requester_id: str) -> dict:
    """Delete a vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to delete.
        requester_id (str): ID of the user requesting the deletion.

    Returns:
        dict: Confirmation message of deletion.

    Raises:
        ValidationError: If vendor_id or requester_id is invalid.
        NotFoundError: If vendor is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    db_helper = DBHelper()
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor ID format: {vendor_id}")
        if not ObjectId.is_valid(requester_id):
            raise ValidationError(f"Invalid requester_id format: {requester_id}")

        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")

        if requester_id != vendor_id:
            requester = db_helper.find_one("users", {"_id": ObjectId(requester_id)})
            if not requester or "admin" not in requester.get("roles", []):
                raise UnauthorizedError("You can only delete your own account unless you are an admin")

        db.vendors.delete_one({"_id": ObjectId(vendor_id)})
        logger.info(f"Vendor deleted: {vendor_id}")
        return {"message": f"Vendor {vendor_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_vendor: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_vendor: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_vendor: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete vendor: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_vendor: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete vendor: {str(e)}")

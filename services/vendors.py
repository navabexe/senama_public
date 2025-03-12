# services/vendors.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, InternalServerError, UnauthorizedError
from core.utils.validation import validate_object_id
from domain.entities.vendor import Vendor
from domain.schemas.vendor import VendorCreate, VendorUpdate
from domain.schemas.notification import NotificationCreate

logger = logging.getLogger(__name__)

class VendorService:
    def __init__(self, db: Database):
        """Initialize VendorService with a database instance."""
        self.db = db

    def create_vendor(self, vendor_data: Dict[str, Any]) -> Dict[str, str]:
        """Create a new vendor with atomic check to prevent duplicates and notify admins.

        Args:
            vendor_data (Dict[str, Any]): Data for the vendor including username, name, owner_name, phone, etc.

        Returns:
            Dict[str, str]: Dictionary containing the created vendor ID.

        Raises:
            ValidationError: If required fields are missing, invalid, or username/phone is taken.
            NotFoundError: If any business category is not found.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            vendor_create = VendorCreate(**vendor_data)  # اعتبارسنجی با Pydantic
            vendor_data_validated = vendor_create.model_dump()

            for category_id in vendor_data_validated["business_category_ids"]:
                validate_object_id(category_id, "category_id")
                if not self.db.business_categories.find_one({"_id": ObjectId(category_id)}):
                    raise NotFoundError(f"Business category with ID {category_id} not found")

            with self.db.client.start_session() as session:
                with session.start_transaction():
                    if self.db.vendors.find_one({"username": vendor_data_validated["username"]}, session=session):
                        raise ValidationError("Username already taken")
                    if self.db.vendors.find_one({"phone": vendor_data_validated["phone"]}, session=session):
                        raise ValidationError("Phone number already registered")

                    vendor = Vendor(**vendor_data_validated)
                    result = self.db.vendors.insert_one(vendor.model_dump(exclude={"id"}), session=session)
                    vendor_id = str(result.inserted_id)

                    admins = self.db.users.find({"roles": {"$in": ["admin"]}}, session=session)
                    for admin in admins:
                        notification_data = NotificationCreate(
                            user_id=str(admin["_id"]),
                            vendor_id=None,
                            type="vendor_verification",
                            message=f"New vendor {vendor_data_validated['username']} (ID: {vendor_id}) awaiting verification",
                            status="unread",
                            related_id=vendor_id
                        ).model_dump()
                        self.db.notifications.insert_one(notification_data, session=session)

            logger.info(f"Vendor created with ID: {vendor_id}")
            return {"id": vendor_id}
        except ValidationError as ve:
            logger.error(f"Validation error in create_vendor: {ve.detail}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error in create_vendor: {ne.detail}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database operation failed in create_vendor: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to create vendor: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in create_vendor: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to create vendor: {str(e)}")

    def get_vendor(self, vendor_id: str, requester_id: str = None) -> Vendor:
        """Retrieve a vendor by their ID.

        Args:
            vendor_id (str): ID of the vendor to retrieve.
            requester_id (str, optional): ID of the user requesting the data, for authorization check.

        Returns:
            Vendor: The requested vendor object.

        Raises:
            ValidationError: If vendor_id or requester_id format is invalid.
            NotFoundError: If vendor is not found.
            UnauthorizedError: If requester is not authorized (when applicable).
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(vendor_id, "vendor_id")
            if requester_id:
                validate_object_id(requester_id, "requester_id")

            vendor = self.db.vendors.find_one({"_id": ObjectId(vendor_id)})
            if not vendor:
                raise NotFoundError(f"Vendor with ID {vendor_id} not found")

            if requester_id and requester_id != vendor_id:
                requester = self.db.users.find_one({"_id": ObjectId(requester_id)})
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

    def update_vendor(self, vendor_id: str, requester_id: str, update_data: Dict[str, Any]) -> Vendor:
        """Update an existing vendor.

        Args:
            vendor_id (str): ID of the vendor to update.
            requester_id (str): ID of the user or vendor requesting the update.
            update_data (Dict[str, Any]): Data to update in the vendor (e.g., name, address).

        Returns:
            Vendor: The updated vendor object.

        Raises:
            ValidationError: If vendor_id, requester_id, or data is invalid.
            NotFoundError: If vendor or business category is not found.
            UnauthorizedError: If requester is not authorized.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(vendor_id, "vendor_id")
            validate_object_id(requester_id, "requester_id")
            vendor_update = VendorUpdate(**update_data)  # اعتبارسنجی با Pydantic
            update_data_validated = vendor_update.model_dump(exclude_unset=True)

            vendor = self.db.vendors.find_one({"_id": ObjectId(vendor_id)})
            if not vendor:
                raise NotFoundError(f"Vendor with ID {vendor_id} not found")

            if requester_id != vendor_id:
                requester = self.db.users.find_one({"_id": ObjectId(requester_id)})
                if not requester or "admin" not in requester.get("roles", []):
                    raise UnauthorizedError("You can only update your own profile unless you are an admin")

            if "business_category_ids" in update_data_validated:
                for category_id in update_data_validated["business_category_ids"]:
                    validate_object_id(category_id, "category_id")
                    if not self.db.business_categories.find_one({"_id": ObjectId(category_id)}):
                        raise NotFoundError(f"Business category with ID {category_id} not found")

            if "username" in update_data_validated and update_data_validated["username"] != vendor["username"]:
                if self.db.vendors.find_one({"username": update_data_validated["username"]}):
                    raise ValidationError("Username already taken")

            if "phone" in update_data_validated and update_data_validated["phone"] != vendor["phone"]:
                if self.db.vendors.find_one({"phone": update_data_validated["phone"]}):
                    raise ValidationError("Phone number already registered")

            update_data_validated["updated_at"] = datetime.now(timezone.utc)
            updated = self.db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$set": update_data_validated})
            if updated.matched_count == 0:
                raise InternalServerError(f"Failed to update vendor {vendor_id}")

            updated_vendor = self.db.vendors.find_one({"_id": ObjectId(vendor_id)})
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

    def delete_vendor(self, vendor_id: str, requester_id: str) -> Dict[str, str]:
        """Delete a vendor.

        Args:
            vendor_id (str): ID of the vendor to delete.
            requester_id (str): ID of the user requesting the deletion.

        Returns:
            Dict[str, str]: Confirmation message of deletion.

        Raises:
            ValidationError: If vendor_id or requester_id is invalid.
            NotFoundError: If vendor is not found.
            UnauthorizedError: If requester is not authorized.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(vendor_id, "vendor_id")
            validate_object_id(requester_id, "requester_id")

            vendor = self.db.vendors.find_one({"_id": ObjectId(vendor_id)})
            if not vendor:
                raise NotFoundError(f"Vendor with ID {vendor_id} not found")

            if requester_id != vendor_id:
                requester = self.db.users.find_one({"_id": ObjectId(requester_id)})
                if not requester or "admin" not in requester.get("roles", []):
                    raise UnauthorizedError("You can only delete your own account unless you are an admin")

            self.db.vendors.delete_one({"_id": ObjectId(vendor_id)})
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

    def get_all_vendors(self) -> List[Vendor]:
        """Get all vendors (admin only)."""
        try:
            vendors = list(self.db.vendors.find())
            if not vendors:
                logger.debug("No vendors found in the database")
                return []
            logger.info(f"Retrieved {len(vendors)} vendors")
            return [Vendor(**vendor) for vendor in vendors]
        except OperationFailure as of:
            logger.error(f"Database operation failed in get_all_vendors: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to get all vendors: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in get_all_vendors: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to get all vendors: {str(e)}")

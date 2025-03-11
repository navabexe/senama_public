# services/advertisements.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from domain.entities.advertisement import Advertisement

logger = logging.getLogger(__name__)


def create_advertisement(db: Database, vendor_id: str, ad_data: dict) -> dict:
    """Create a new advertisement for a vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor creating the advertisement as a string.
        ad_data (dict): Advertisement data including type, related_id, cost, etc.

    Returns:
        dict: Dictionary containing the created advertisement ID as a string.

    Raises:
        ValidationError: If input data or IDs are invalid.
        NotFoundError: If vendor or related entity is not found.
        UnauthorizedError: If vendor tries to advertise another's content.
        InternalServerError: For unexpected database or system errors.
    """
    try:
        # اعتبارسنجی vendor_id
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")
        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")
        if vendor["wallet_balance"] < ad_data["cost"]:
            raise ValidationError("Insufficient wallet balance")

        # اعتبارسنجی related_id
        if not ObjectId.is_valid(ad_data["related_id"]):
            raise ValidationError(f"Invalid related_id format: {ad_data['related_id']}")
        related_collection = "stories" if ad_data["type"] == "story" else "products"
        related = db[related_collection].find_one({"_id": ObjectId(ad_data["related_id"])})
        if not related:
            raise NotFoundError(f"Related {ad_data['type']} with ID {ad_data['related_id']} not found")
        if related["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only advertise your own content")

        ad_data["vendor_id"] = vendor_id
        advertisement = Advertisement(**ad_data)
        result = db.advertisements.insert_one(advertisement.model_dump(exclude={"id"}))
        ad_id = str(result.inserted_id)
        logger.info(f"Advertisement created with ID: {ad_id} by vendor: {vendor_id}")
        return {"id": ad_id}

    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise ue
    except DuplicateKeyError:
        logger.error("Duplicate advertisement detected")
        raise ValidationError("An advertisement with this data already exists")
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise InternalServerError(f"Database error: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Unexpected error occurred: {str(e)}")


def get_advertisement(db: Database, ad_id: str, vendor_id: str) -> Advertisement:
    """Retrieve an advertisement by its ID.

    Args:
        db (Database): MongoDB database instance.
        ad_id (str): ID of the advertisement to retrieve as a string.
        vendor_id (str): ID of the vendor requesting the advertisement as a string.

    Returns:
        Advertisement: The requested advertisement object.

    Raises:
        ValidationError: If ad_id or vendor_id format is invalid.
        NotFoundError: If advertisement is not found.
        UnauthorizedError: If vendor is not authorized to view the advertisement.
        InternalServerError: For unexpected errors.
    """
    try:
        if not ObjectId.is_valid(ad_id):
            raise ValidationError(f"Invalid advertisement ID format: {ad_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        advertisement = db.advertisements.find_one({"_id": ObjectId(ad_id)})
        if not advertisement:
            raise NotFoundError(f"Advertisement with ID {ad_id} not found")
        if advertisement["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only view your own advertisements")

        # بررسی وضعیت بر اساس زمان
        now = datetime.now(timezone.utc)
        if advertisement["status"] == "active" and advertisement["ends_at"] < now:
            db.advertisements.update_one({"_id": ObjectId(ad_id)}, {"$set": {"status": "expired"}})
            advertisement["status"] = "expired"

        logger.info(f"Advertisement retrieved: {ad_id}")
        return Advertisement(**advertisement)

    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise InternalServerError(f"Database error: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get advertisement: {str(e)}")


def update_advertisement(db: Database, ad_id: str, vendor_id: str, update_data: dict) -> Advertisement:
    """Update an existing advertisement.

    Args:
        db (Database): MongoDB database instance.
        ad_id (str): ID of the advertisement to update as a string.
        vendor_id (str): ID of the vendor updating the advertisement as a string.
        update_data (dict): Data to update in the advertisement.

    Returns:
        Advertisement: The updated advertisement object.

    Raises:
        ValidationError: If input data or IDs are invalid.
        NotFoundError: If advertisement is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors.
    """
    try:
        if not ObjectId.is_valid(ad_id):
            raise ValidationError(f"Invalid advertisement ID format: {ad_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        advertisement = db.advertisements.find_one({"_id": ObjectId(ad_id)})
        if not advertisement:
            raise NotFoundError(f"Advertisement with ID {ad_id} not found")
        if advertisement["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only update your own advertisements")

        update_data["updated_at"] = datetime.now(timezone.utc)

        # کسر هزینه از کیف پول اگه به active تغییر کنه
        if "status" in update_data and update_data["status"] == "active" and advertisement["status"] != "active":
            vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
            if vendor["wallet_balance"] < advertisement["cost"]:
                raise ValidationError("Insufficient wallet balance")
            db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$inc": {"wallet_balance": -advertisement["cost"]}})

        db.advertisements.update_one({"_id": ObjectId(ad_id)}, {"$set": update_data})
        updated_advertisement = db.advertisements.find_one({"_id": ObjectId(ad_id)})
        logger.info(f"Advertisement updated: {ad_id}")
        return Advertisement(**updated_advertisement)

    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise InternalServerError(f"Database error: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update advertisement: {str(e)}")


def delete_advertisement(db: Database, ad_id: str, vendor_id: str) -> dict:
    """Delete an advertisement.

    Args:
        db (Database): MongoDB database instance.
        ad_id (str): ID of the advertisement to delete as a string.
        vendor_id (str): ID of the vendor deleting the advertisement as a string.

    Returns:
        dict: Confirmation message of deletion.

    Raises:
        ValidationError: If IDs or status are invalid.
        NotFoundError: If advertisement is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors.
    """
    try:
        if not ObjectId.is_valid(ad_id):
            raise ValidationError(f"Invalid advertisement ID format: {ad_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        advertisement = db.advertisements.find_one({"_id": ObjectId(ad_id)})
        if not advertisement:
            raise NotFoundError(f"Advertisement with ID {ad_id} not found")
        if advertisement["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only delete your own advertisements")
        if advertisement["status"] != "pending":
            raise ValidationError("Only pending advertisements can be deleted")

        db.advertisements.delete_one({"_id": ObjectId(ad_id)})
        logger.info(f"Advertisement deleted: {ad_id}")
        return {"message": f"Advertisement {ad_id} deleted successfully"}

    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise InternalServerError(f"Database error: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete advertisement: {str(e)}")


def get_advertisements_by_vendor(db: Database, vendor_id: str) -> list[Advertisement]:
    """Retrieve all advertisements for a specific vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve advertisements for.

    Returns:
        list[Advertisement]: List of advertisement objects.

    Raises:
        ValidationError: If vendor_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        advertisements = list(db.advertisements.find({"vendor_id": vendor_id}))
        if not advertisements:
            logger.debug(f"No advertisements found for vendor_id: {vendor_id}")
            return []

        logger.info(f"Retrieved {len(advertisements)} advertisements for vendor_id: {vendor_id}")
        return [Advertisement(**advertisement) for advertisement in advertisements]
    except ValidationError as ve:
        logger.error(f"Validation error in get_advertisements_by_vendor: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_advertisements_by_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get advertisements: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_advertisements_by_vendor: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get advertisements: {str(e)}")

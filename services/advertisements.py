# services/advertisements.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.advertisement import Advertisement
from domain.schemas.advertisement import AdvertisementCreate, AdvertisementUpdate

logger = logging.getLogger(__name__)

def create_advertisement(db: Database, vendor_id: str, ad_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new advertisement for a vendor with transaction."""
    try:
        validate_object_id(vendor_id, "vendor_id")
        ad_create = AdvertisementCreate(**ad_data)
        ad_data_validated = ad_create.model_dump()

        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")
        if vendor["wallet_balance"] < ad_data_validated["cost"]:
            raise ValidationError("Insufficient wallet balance")

        validate_object_id(ad_data_validated["related_id"], "related_id")
        related_collection = "stories" if ad_data_validated["type"] == "story" else "products"
        related = db[related_collection].find_one({"_id": ObjectId(ad_data_validated["related_id"])})
        if not related:
            raise NotFoundError(f"Related {ad_data_validated['type']} with ID {ad_data_validated['related_id']} not found")
        if related["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only advertise your own content")

        advertisement = Advertisement(**ad_data_validated, vendor_id=vendor_id)
        with db.client.start_session() as session:
            with session.start_transaction():
                result = db.advertisements.insert_one(advertisement.model_dump(exclude={"id"}), session=session)
                ad_id = str(result.inserted_id)
                logger.info(f"Advertisement created with ID: {ad_id} by vendor: {vendor_id}")
                return {"id": ad_id}

    except (ValidationError, NotFoundError, UnauthorizedError) as e:
        logger.error(f"Error in create_advertisement: {e.detail}")
        raise e
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
    """Retrieve an advertisement by its ID."""
    try:
        validate_object_id(ad_id, "advertisement_id")
        validate_object_id(vendor_id, "vendor_id")

        advertisement = db.advertisements.find_one({"_id": ObjectId(ad_id)})
        if not advertisement:
            raise NotFoundError(f"Advertisement with ID {ad_id} not found")
        if advertisement["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only view your own advertisements")

        now = datetime.now(timezone.utc)
        if advertisement["status"] == "active" and advertisement["ends_at"] < now:
            db.advertisements.update_one({"_id": ObjectId(ad_id)}, {"$set": {"status": "expired"}})
            advertisement["status"] = "expired"

        logger.info(f"Advertisement retrieved: {ad_id}")
        return Advertisement(**advertisement)
    except (ValidationError, NotFoundError, UnauthorizedError) as e:
        logger.error(f"Error in get_advertisement: {e.detail}")
        raise e
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise InternalServerError(f"Database error: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get advertisement: {str(e)}")

def update_advertisement(db: Database, ad_id: str, vendor_id: str, update_data: Dict[str, Any]) -> Advertisement:
    """Update an existing advertisement with transaction for wallet updates."""
    try:
        validate_object_id(ad_id, "advertisement_id")
        validate_object_id(vendor_id, "vendor_id")
        ad_update = AdvertisementUpdate(**update_data)
        update_data_validated = ad_update.model_dump(exclude_unset=True)

        advertisement = db.advertisements.find_one({"_id": ObjectId(ad_id)})
        if not advertisement:
            raise NotFoundError(f"Advertisement with ID {ad_id} not found")
        if advertisement["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only update your own advertisements")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)

        if "status" in update_data_validated and update_data_validated["status"] == "active" and advertisement["status"] != "active":
            with db.client.start_session() as session:
                with session.start_transaction():
                    vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)}, session=session)
                    if vendor["wallet_balance"] < advertisement["cost"]:
                        raise ValidationError("Insufficient wallet balance")
                    db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$inc": {"wallet_balance": -advertisement["cost"]}}, session=session)
                    db.advertisements.update_one({"_id": ObjectId(ad_id)}, {"$set": update_data_validated}, session=session)
        else:
            db.advertisements.update_one({"_id": ObjectId(ad_id)}, {"$set": update_data_validated})

        updated_advertisement = db.advertisements.find_one({"_id": ObjectId(ad_id)})
        logger.info(f"Advertisement updated: {ad_id}")
        return Advertisement(**updated_advertisement)
    except (ValidationError, NotFoundError, UnauthorizedError) as e:
        logger.error(f"Error in update_advertisement: {e.detail}")
        raise e
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise InternalServerError(f"Database error: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update advertisement: {str(e)}")

def delete_advertisement(db: Database, ad_id: str, vendor_id: str) -> Dict[str, str]:
    """Delete an advertisement."""
    try:
        validate_object_id(ad_id, "advertisement_id")
        validate_object_id(vendor_id, "vendor_id")

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
    except (ValidationError, NotFoundError, UnauthorizedError) as e:
        logger.error(f"Error in delete_advertisement: {e.detail}")
        raise e
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise InternalServerError(f"Database error: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete advertisement: {str(e)}")

def get_advertisements_by_vendor(db: Database, vendor_id: str) -> List[Advertisement]:
    """Retrieve all advertisements for a specific vendor."""
    try:
        validate_object_id(vendor_id, "vendor_id")

        advertisements = list(db.advertisements.find({"vendor_id": vendor_id}))
        if not advertisements:
            logger.debug(f"No advertisements found for vendor_id: {vendor_id}")
            return []

        logger.info(f"Retrieved {len(advertisements)} advertisements for vendor_id: {vendor_id}")
        return [Advertisement(**advertisement) for advertisement in advertisements]
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get advertisements: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get advertisements: {str(e)}")
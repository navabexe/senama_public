# services/collaborations.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from domain.entities.collaboration import Collaboration

logger = logging.getLogger(__name__)


def create_collaboration(db: Database, requester_vendor_id: str, collaboration_data: dict) -> dict:
    """Create a new collaboration request between vendors.

    Args:
        db (Database): MongoDB database instance.
        requester_vendor_id (str): ID of the vendor requesting the collaboration.
        collaboration_data (dict): Data for the collaboration including target_vendor_id and product_id.

    Returns:
        dict: Dictionary containing the created collaboration ID.

    Raises:
        ValidationError: If required fields are missing or invalid.
        NotFoundError: If target vendor or product is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(requester_vendor_id):
            raise ValidationError(f"Invalid requester_vendor_id format: {requester_vendor_id}")
        if not collaboration_data.get("target_vendor_id") or not collaboration_data.get("product_id"):
            raise ValidationError("Target vendor ID and product ID are required")
        if not ObjectId.is_valid(collaboration_data["target_vendor_id"]):
            raise ValidationError(f"Invalid target_vendor_id format: {collaboration_data['target_vendor_id']}")
        if not ObjectId.is_valid(collaboration_data["product_id"]):
            raise ValidationError(f"Invalid product_id format: {collaboration_data['product_id']}")

        target_vendor = db.vendors.find_one({"_id": ObjectId(collaboration_data["target_vendor_id"])})
        if not target_vendor:
            raise NotFoundError(f"Target vendor with ID {collaboration_data['target_vendor_id']} not found")

        product = db.products.find_one({"_id": ObjectId(collaboration_data["product_id"])})
        if not product:
            raise NotFoundError(f"Product with ID {collaboration_data['product_id']} not found")
        if product["vendor_id"] != collaboration_data["target_vendor_id"]:
            raise ValidationError("Product does not belong to the target vendor")

        collaboration_data["requester_vendor_id"] = requester_vendor_id
        collaboration = Collaboration(**collaboration_data)
        result = db.collaborations.insert_one(collaboration.model_dump(exclude={"id"}))
        collaboration_id = str(result.inserted_id)
        logger.info(f"Collaboration created with ID: {collaboration_id}")
        return {"id": collaboration_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_collaboration: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_collaboration: {ne.detail}")
        raise ne
    except DuplicateKeyError:
        logger.error("Duplicate collaboration detected")
        raise ValidationError("This collaboration already exists")
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_collaboration: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create collaboration: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_collaboration: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create collaboration: {str(e)}")


def get_collaboration(db: Database, collaboration_id: str, vendor_id: str) -> Collaboration:
    """Retrieve a collaboration by its ID.

    Args:
        db (Database): MongoDB database instance.
        collaboration_id (str): ID of the collaboration to retrieve.
        vendor_id (str): ID of the vendor requesting the collaboration.

    Returns:
        Collaboration: The requested collaboration object.

    Raises:
        ValidationError: If collaboration_id or vendor_id is invalid.
        NotFoundError: If collaboration is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(collaboration_id):
            raise ValidationError(f"Invalid collaboration ID format: {collaboration_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        collaboration = db.collaborations.find_one({"_id": ObjectId(collaboration_id)})
        if not collaboration:
            raise NotFoundError(f"Collaboration with ID {collaboration_id} not found")
        if collaboration["requester_vendor_id"] != vendor_id and collaboration["target_vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only view your own collaborations")

        logger.info(f"Collaboration retrieved: {collaboration_id}")
        return Collaboration(**collaboration)
    except ValidationError as ve:
        logger.error(f"Validation error in get_collaboration: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_collaboration: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_collaboration: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_collaboration: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get collaboration: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_collaboration: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get collaboration: {str(e)}")


def get_collaborations_by_vendor(db: Database, vendor_id: str) -> list[Collaboration]:
    """Retrieve all collaborations for a specific vendor (as requester or target).

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve collaborations for.

    Returns:
        list[Collaboration]: List of collaboration objects.

    Raises:
        ValidationError: If vendor_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        collaborations = list(db.collaborations.find({
            "$or": [
                {"requester_vendor_id": vendor_id},
                {"target_vendor_id": vendor_id}
            ]
        }))
        if not collaborations:
            logger.debug(f"No collaborations found for vendor_id: {vendor_id}")
            return []

        logger.info(f"Retrieved {len(collaborations)} collaborations for vendor: {vendor_id}")
        return [Collaboration(**collab) for collab in collaborations]
    except ValidationError as ve:
        logger.error(f"Validation error in get_collaborations_by_vendor: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_collaborations_by_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get collaborations: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_collaborations_by_vendor: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get collaborations: {str(e)}")


def update_collaboration(db: Database, collaboration_id: str, vendor_id: str, update_data: dict) -> Collaboration:
    """Update an existing collaboration.

    Args:
        db (Database): MongoDB database instance.
        collaboration_id (str): ID of the collaboration to update.
        vendor_id (str): ID of the vendor updating the collaboration.
        update_data (dict): Data to update in the collaboration.

    Returns:
        Collaboration: The updated collaboration object.

    Raises:
        ValidationError: If collaboration_id, vendor_id, or status is invalid.
        NotFoundError: If collaboration is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(collaboration_id):
            raise ValidationError(f"Invalid collaboration ID format: {collaboration_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        collaboration = db.collaborations.find_one({"_id": ObjectId(collaboration_id)})
        if not collaboration:
            raise NotFoundError(f"Collaboration with ID {collaboration_id} not found")
        if collaboration["target_vendor_id"] != vendor_id:
            raise UnauthorizedError("Only the target vendor can update collaboration status")

        update_data["updated_at"] = datetime.now(timezone.utc)
        if "status" in update_data and update_data["status"] not in ["pending", "accepted", "rejected"]:
            raise ValidationError("Invalid status value")

        # به‌روزرسانی لیست linked_vendors در محصول اگه پذیرفته شد
        if "status" in update_data and update_data["status"] == "accepted" and collaboration["status"] != "accepted":
            updated = db.products.update_one(
                {"_id": ObjectId(collaboration["product_id"])},
                {"$push": {"linked_vendors": collaboration["requester_vendor_id"]}}
            )
            if updated.matched_count == 0:
                raise InternalServerError(
                    f"Failed to update product linked_vendors for collaboration {collaboration_id}")

        updated = db.collaborations.update_one({"_id": ObjectId(collaboration_id)}, {"$set": update_data})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update collaboration {collaboration_id}")

        updated_collaboration = db.collaborations.find_one({"_id": ObjectId(collaboration_id)})
        logger.info(f"Collaboration updated: {collaboration_id}")
        return Collaboration(**updated_collaboration)
    except ValidationError as ve:
        logger.error(f"Validation error in update_collaboration: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_collaboration: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_collaboration: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_collaboration: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update collaboration: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_collaboration: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update collaboration: {str(e)}")


def delete_collaboration(db: Database, collaboration_id: str, vendor_id: str) -> dict:
    """Delete a collaboration.

    Args:
        db (Database): MongoDB database instance.
        collaboration_id (str): ID of the collaboration to delete.
        vendor_id (str): ID of the vendor deleting the collaboration.

    Returns:
        dict: Confirmation message of deletion.

    Raises:
        ValidationError: If collaboration_id, vendor_id, or status is invalid.
        NotFoundError: If collaboration is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(collaboration_id):
            raise ValidationError(f"Invalid collaboration ID format: {collaboration_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        collaboration = db.collaborations.find_one({"_id": ObjectId(collaboration_id)})
        if not collaboration:
            raise NotFoundError(f"Collaboration with ID {collaboration_id} not found")
        if collaboration["requester_vendor_id"] != vendor_id:
            raise UnauthorizedError("Only the requester vendor can delete a collaboration")
        if collaboration["status"] != "pending":
            raise ValidationError("Only pending collaborations can be deleted")

        db.collaborations.delete_one({"_id": ObjectId(collaboration_id)})
        logger.info(f"Collaboration deleted: {collaboration_id}")
        return {"message": f"Collaboration {collaboration_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_collaboration: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_collaboration: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_collaboration: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_collaboration: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete collaboration: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_collaboration: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete collaboration: {str(e)}")

# services/reports.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.report import Report
from domain.schemas.report import ReportCreate, ReportUpdate

logger = logging.getLogger(__name__)

def create_report(db: Database, reporter_id: str, report_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new report for a user or vendor with atomic check to prevent duplicates.

    Args:
        db (Database): MongoDB database instance.
        reporter_id (str): ID of the user or vendor submitting the report.
        report_data (Dict[str, Any]): Data for the report including target_id, target_type, and reason.

    Returns:
        Dict[str, str]: Dictionary containing the created report ID.

    Raises:
        ValidationError: If required fields are missing, invalid, or report already exists.
        NotFoundError: If the target entity is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(reporter_id, "reporter_id")
        report_create = ReportCreate(**report_data)  # اعتبارسنجی با Pydantic
        report_data_validated = report_create.model_dump()

        validate_object_id(report_data_validated["target_id"], "target_id")
        if reporter_id == report_data_validated["target_id"]:
            raise ValidationError("You cannot report yourcls")

        # بررسی وجود موجودیت هدف
        target = None
        if report_data_validated["target_type"] == "user":
            target = db.users.find_one({"_id": ObjectId(report_data_validated["target_id"])})
        elif report_data_validated["target_type"] == "vendor":
            target = db.vendors.find_one({"_id": ObjectId(report_data_validated["target_id"])})
        elif report_data_validated["target_type"] == "product":
            target = db.products.find_one({"_id": ObjectId(report_data_validated["target_id"])})
        if not target:
            raise NotFoundError(f"Target {report_data_validated['target_type']} with ID {report_data_validated['target_id']} not found")

        report_data_validated["reporter_id"] = reporter_id
        report = Report(**report_data_validated)

        with db.client.start_session() as session:
            with session.start_transaction():
                # بررسی اتمی برای جلوگیری از گزارش تکراری
                query = {
                    "reporter_id": reporter_id,
                    "target_id": report_data_validated["target_id"],
                    "target_type": report_data_validated["target_type"]
                }
                existing_report = db.reports.find_one(query, session=session)
                if existing_report:
                    raise ValidationError(f"A report for this target already exists by reporter {reporter_id}")

                result = db.reports.insert_one(report.model_dump(exclude={"id"}), session=session)
                report_id = str(result.inserted_id)

        logger.info(f"Report created with ID: {report_id} by: {reporter_id}")
        return {"id": report_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_report: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_report: {ne.detail}")
        raise ne
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_report: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create report: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_report: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create report: {str(e)}")

def get_report(db: Database, report_id: str, user_id: str) -> Report:
    """Retrieve a report by its ID.

    Args:
        db (Database): MongoDB database instance.
        report_id (str): ID of the report to retrieve.
        user_id (str): ID of the user or vendor requesting the report.

    Returns:
        Report: The requested report object.

    Raises:
        ValidationError: If report_id or user_id is invalid.
        NotFoundError: If report is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(report_id, "report_id")
        validate_object_id(user_id, "user_id")

        report = db.reports.find_one({"_id": ObjectId(report_id)})
        if not report:
            raise NotFoundError(f"Report with ID {report_id} not found")
        if report["reporter_id"] != user_id:
            user = db.users.find_one({"_id": ObjectId(user_id)})
            if not user or "admin" not in user.get("roles", []):
                raise UnauthorizedError("You can only view your own reports unless you are an admin")

        logger.info(f"Report retrieved: {report_id}")
        return Report(**report)
    except ValidationError as ve:
        logger.error(f"Validation error in get_report: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_report: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_report: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_report: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get report: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_report: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get report: {str(e)}")

def get_reports_by_reporter(db: Database, reporter_id: str) -> List[Report]:
    """Retrieve all reports submitted by a specific reporter.

    Args:
        db (Database): MongoDB database instance.
        reporter_id (str): ID of the user or vendor to retrieve reports for.

    Returns:
        List[Report]: List of report objects.

    Raises:
        ValidationError: If reporter_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(reporter_id, "reporter_id")

        reports = list(db.reports.find({"reporter_id": reporter_id}))
        if not reports:
            logger.debug(f"No reports found for reporter_id: {reporter_id}")
            return []

        logger.info(f"Retrieved {len(reports)} reports for reporter_id: {reporter_id}")
        return [Report(**report) for report in reports]
    except ValidationError as ve:
        logger.error(f"Validation error in get_reports_by_reporter: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_reports_by_reporter: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get reports: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_reports_by_reporter: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get reports: {str(e)}")

def update_report(db: Database, report_id: str, user_id: str, update_data: Dict[str, Any]) -> Report:
    """Update an existing report (admin only).

    Args:
        db (Database): MongoDB database instance.
        report_id (str): ID of the report to update.
        user_id (str): ID of the user updating the report.
        update_data (Dict[str, Any]): Data to update in the report (e.g., status).

    Returns:
        Report: The updated report object.

    Raises:
        ValidationError: If report_id, user_id, or status is invalid.
        NotFoundError: If report is not found.
        UnauthorizedError: If requester is not an admin.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(report_id, "report_id")
        validate_object_id(user_id, "user_id")
        report_update = ReportUpdate(**update_data)  # اعتبارسنجی با Pydantic
        update_data_validated = report_update.model_dump(exclude_unset=True)

        report = db.reports.find_one({"_id": ObjectId(report_id)})
        if not report:
            raise NotFoundError(f"Report with ID {report_id} not found")

        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user or "admin" not in user.get("roles", []):
            raise UnauthorizedError("Only admins can update reports")

        update_data_validated["updated_at"] = datetime.now(timezone.utc)
        updated = db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": update_data_validated})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update report {report_id}")

        updated_report = db.reports.find_one({"_id": ObjectId(report_id)})
        logger.info(f"Report updated: {report_id}")
        return Report(**updated_report)
    except ValidationError as ve:
        logger.error(f"Validation error in update_report: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_report: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_report: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_report: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update report: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_report: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update report: {str(e)}")

def delete_report(db: Database, report_id: str, user_id: str) -> Dict[str, str]:
    """Delete a report.

    Args:
        db (Database): MongoDB database instance.
        report_id (str): ID of the report to delete.
        user_id (str): ID of the user deleting the report.

    Returns:
        Dict[str, str]: Confirmation message of deletion.

    Raises:
        ValidationError: If report_id or user_id is invalid.
        NotFoundError: If report is not found.
        UnauthorizedError: If requester is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        validate_object_id(report_id, "report_id")
        validate_object_id(user_id, "user_id")

        report = db.reports.find_one({"_id": ObjectId(report_id)})
        if not report:
            raise NotFoundError(f"Report with ID {report_id} not found")
        if report["reporter_id"] != user_id:
            raise UnauthorizedError("You can only delete your own reports")
        if report["status"] != "pending":
            raise ValidationError("Only pending reports can be deleted")

        db.reports.delete_one({"_id": ObjectId(report_id)})
        logger.info(f"Report deleted: {report_id}")
        return {"message": f"Report {report_id} deleted successfully"}
    except ValidationError as ve:
        logger.error(f"Validation error in delete_report: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in delete_report: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in delete_report: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in delete_report: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to delete report: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_report: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete report: {str(e)}")
# routes/v1/reports.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, ValidationError, NotFoundError
from domain.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from infrastructure.database.client import get_db
from services.reports import create_report, get_report, get_reports_by_reporter, update_report, delete_report
import logging

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@router.post("", response_model=dict, summary="Create a new report")
@limiter.limit("5/minute")
async def create_report_route(
    request: Request,
    report_data: ReportCreate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        reporter_id = str(current_user["_id"])
        result = create_report(db, reporter_id, report_data.model_dump())
        logger.info(f"Report created by user {reporter_id}: {result['id']}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to create report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{report_id}", response_model=ReportResponse, summary="Get report by ID")
@limiter.limit("10/minute")
async def get_report_route(
    request: Request,
    report_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        report = get_report(db, report_id, user_id)
        logger.info(f"Report retrieved: {report_id} by user: {user_id}")
        return report
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve report {report_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reporter/{reporter_id}", response_model=list[ReportResponse], summary="Get all reports by reporter")
@limiter.limit("10/minute")
async def get_reporter_reports_route(
    request: Request,
    reporter_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        requester_id = str(current_user["_id"])
        if requester_id != reporter_id and "admin" not in current_user["roles"]:
            raise UnauthorizedError("You can only view your own reports unless you are an admin")
        reports = get_reports_by_reporter(db, reporter_id)
        logger.info(f"Retrieved {len(reports)} reports for reporter: {reporter_id}")
        return reports
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve reports for reporter {reporter_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{report_id}", response_model=ReportResponse, summary="Update report")
@limiter.limit("5/minute")
async def update_report_route(
    request: Request,
    report_id: str,
    update_data: ReportUpdate,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        if "admin" not in current_user["roles"]:
            raise UnauthorizedError("Only admins can update reports")
        report = update_report(db, report_id, user_id, update_data.model_dump(exclude_unset=True))
        logger.info(f"Report updated: {report_id} by admin: {user_id}")
        return report
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to update report {report_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{report_id}", response_model=dict, summary="Delete report")
@limiter.limit("5/minute")
async def delete_report_route(
    request: Request,
    report_id: str,
    db: Database = Depends(get_db),
    token: str = Depends(get_token)
):
    try:
        current_user = get_current_user(token, db)
        user_id = str(current_user["_id"])
        result = delete_report(db, report_id, user_id)
        logger.info(f"Report deleted: {report_id} by user: {user_id}")
        return result
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.detail}")
        raise HTTPException(status_code=400, detail=ve.detail)
    except NotFoundError as ne:
        logger.error(f"Not found error: {ne.detail}")
        raise HTTPException(status_code=404, detail=ne.detail)
    except Exception as e:
        logger.error(f"Failed to delete report {report_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
# routes/v1/reports.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.reports import create_report, get_report, update_report, delete_report
from domain.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict, summary="Create a new report", description="Creates a new report by the authenticated user or vendor.")
@limiter.limit("5/minute")
async def create_report_route(request: Request, report_data: ReportCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return create_report(db, str(current_user["_id"]), report_data.dict())

@router.get("/{report_id}", response_model=ReportResponse, summary="Get report by ID", description="Retrieves a report by its ID for the reporter.")
@limiter.limit("10/minute")
async def get_report_route(request: Request, report_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return get_report(db, report_id, str(current_user["_id"]))

@router.put("/{report_id}", response_model=ReportResponse, summary="Update report", description="Updates report status or notes by an admin.")
@limiter.limit("5/minute")
async def update_report_route(request: Request, report_id: str, update_data: ReportUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return update_report(db, report_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/{report_id}", response_model=dict, summary="Delete report", description="Deletes a pending report by the reporter.")
@limiter.limit("5/minute")
async def delete_report_route(request: Request, report_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    return delete_report(db, report_id, str(current_user["_id"]))
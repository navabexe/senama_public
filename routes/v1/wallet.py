# routes/v1/wallet.py
from fastapi import APIRouter, Depends, Request
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.database.client import get_db
from core.auth.auth import get_current_user, get_token
from services.wallet import create_transaction, get_transaction, update_transaction, delete_transaction
from domain.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from core.errors import UnauthorizedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/transactions", response_model=dict, summary="Create a new transaction", description="Creates a new transaction for the authenticated vendor.")
@limiter.limit("5/minute")
async def create_transaction_route(request: Request, transaction_data: TransactionCreate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can create transactions")
    return create_transaction(db, str(current_user["_id"]), transaction_data.dict())

@router.get("/transactions/{transaction_id}", response_model=TransactionResponse, summary="Get transaction by ID", description="Retrieves a transaction by its ID for the authenticated vendor.")
@limiter.limit("10/minute")
async def get_transaction_route(request: Request, transaction_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can view transactions")
    return get_transaction(db, transaction_id, str(current_user["_id"]))

@router.put("/transactions/{transaction_id}", response_model=TransactionResponse, summary="Update transaction", description="Updates transaction status or details for the authenticated vendor.")
@limiter.limit("5/minute")
async def update_transaction_route(request: Request, transaction_id: str, update_data: TransactionUpdate, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can update transactions")
    return update_transaction(db, transaction_id, str(current_user["_id"]), update_data.dict(exclude_unset=True))

@router.delete("/transactions/{transaction_id}", response_model=dict, summary="Delete transaction", description="Deletes a pending transaction for the authenticated vendor.")
@limiter.limit("5/minute")
async def delete_transaction_route(request: Request, transaction_id: str, db: Database = Depends(get_db), token: str = Depends(get_token)):
    current_user = get_current_user(token, db)
    if "vendor" not in current_user["roles"]:
        raise UnauthorizedError("Only vendors can delete transactions")
    return delete_transaction(db, transaction_id, str(current_user["_id"]))
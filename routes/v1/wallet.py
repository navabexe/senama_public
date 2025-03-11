# routes/v1/wallet.py
import logging

from fastapi import APIRouter, Depends, Request, HTTPException
from pymongo.database import Database
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth.auth import get_current_user, get_token
from core.errors import UnauthorizedError, NotFoundError, ValidationError
from domain.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from infrastructure.database.client import get_db
from services.wallet import create_transaction, get_transaction, get_transactions_by_vendor, update_transaction, \
    delete_transaction

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.post("/transactions", response_model=dict, summary="Create a new transaction")
@limiter.limit("5/minute")
async def create_transaction_route(
        request: Request,
        transaction_data: TransactionCreate,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Create a new transaction (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can create transactions")
        result = create_transaction(db, str(current_user["_id"]), transaction_data.model_dump())
        logger.info(f"Transaction created by vendor {current_user['_id']}: {result['id']}")
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
        logger.error(f"Failed to create transaction: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse,
            summary="Get transaction by ID",
            description="Retrieves a transaction by its ID. Only the vendor or an admin can access this endpoint.")
@limiter.limit("10/minute")
async def get_transaction_route(
        request: Request,
        transaction_id: str,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Get a transaction by ID (vendor or admin only)."""
    try:
        current_user = get_current_user(token, db)
        transaction = get_transaction(db, transaction_id, str(current_user["_id"]))
        if transaction.vendor_id != str(current_user["_id"]) and "admin" not in current_user["roles"]:
            raise UnauthorizedError("You can only view your own transactions or must be an admin")
        logger.info(f"Transaction retrieved by vendor {current_user['_id']}: {transaction_id}")
        return transaction
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
        logger.error(f"Failed to retrieve transaction {transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/transactions", response_model=list[TransactionResponse],
            summary="Get all transactions for the current vendor")
@limiter.limit("10/minute")
async def get_vendor_transactions_route(
        request: Request,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Get all transactions for the current vendor."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can view their transactions")
        transactions = get_transactions_by_vendor(db, str(current_user["_id"]))
        logger.info(f"Transactions retrieved by vendor {current_user['_id']}")
        return transactions
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error: {ue.detail}")
        raise HTTPException(status_code=403, detail=ue.detail)
    except Exception as e:
        logger.error(f"Failed to retrieve transactions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/transactions/{transaction_id}", response_model=TransactionResponse, summary="Update transaction")
@limiter.limit("5/minute")
async def update_transaction_route(
        request: Request,
        transaction_id: str,
        update_data: TransactionUpdate,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Update a transaction (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can update transactions")
        transaction = update_transaction(db, transaction_id, str(current_user["_id"]),
                                         update_data.model_dump(exclude_unset=True))
        logger.info(f"Transaction updated by vendor {current_user['_id']}: {transaction_id}")
        return transaction
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
        logger.error(f"Failed to update transaction {transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/transactions/{transaction_id}", response_model=dict, summary="Delete transaction")
@limiter.limit("5/minute")
async def delete_transaction_route(
        request: Request,
        transaction_id: str,
        db: Database = Depends(get_db),
        token: str = Depends(get_token)
):
    """Delete a transaction (vendor only)."""
    try:
        current_user = get_current_user(token, db)
        if "vendor" not in current_user["roles"]:
            raise UnauthorizedError("Only vendors can delete transactions")
        result = delete_transaction(db, transaction_id, str(current_user["_id"]))
        logger.info(f"Transaction deleted by vendor {current_user['_id']}: {transaction_id}")
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
        logger.error(f"Failed to delete transaction {transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

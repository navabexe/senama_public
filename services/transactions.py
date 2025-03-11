# services/transactions.py
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from domain.entities.transaction import Transaction

logger = logging.getLogger(__name__)


def create_transaction(db: Database, vendor_id: str, transaction_data: dict) -> dict:
    """Create a new transaction for a vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor creating the transaction.
        transaction_data (dict): Data for the transaction including amount and type.

    Returns:
        dict: Dictionary containing the created transaction ID.

    Raises:
        ValidationError: If required fields are missing or invalid.
        NotFoundError: If vendor is not found.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")
        if not transaction_data.get("amount") or not transaction_data.get("type"):
            raise ValidationError("Amount and type are required")
        if not isinstance(transaction_data["amount"], (int, float)) or transaction_data["amount"] <= 0:
            raise ValidationError("Amount must be a positive number")
        if transaction_data["type"] not in ["deposit", "withdrawal"]:
            raise ValidationError("Type must be 'deposit' or 'withdrawal'")

        vendor = db.vendors.find_one({"_id": ObjectId(vendor_id)})
        if not vendor:
            raise NotFoundError(f"Vendor with ID {vendor_id} not found")

        if transaction_data["type"] == "withdrawal" and vendor["wallet_balance"] < transaction_data["amount"]:
            raise ValidationError("Insufficient wallet balance for withdrawal")

        transaction_data["vendor_id"] = vendor_id
        transaction_data["status"] = "pending"  # وضعیت پیش‌فرض
        transaction = Transaction(**transaction_data)
        result = db.transactions.insert_one(transaction.model_dump(exclude={"id"}))
        transaction_id = str(result.inserted_id)

        if transaction_data["type"] == "deposit":
            db.vendors.update_one({"_id": ObjectId(vendor_id)},
                                  {"$inc": {"wallet_balance": transaction_data["amount"]}})
        elif transaction_data["type"] == "withdrawal":
            db.vendors.update_one({"_id": ObjectId(vendor_id)},
                                  {"$inc": {"wallet_balance": -transaction_data["amount"]}})

        logger.info(f"Transaction created with ID: {transaction_id} for vendor: {vendor_id}")
        return {"id": transaction_id}
    except ValidationError as ve:
        logger.error(f"Validation error in create_transaction: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in create_transaction: {ne.detail}")
        raise ne
    except DuplicateKeyError:
        logger.error("Duplicate transaction detected")
        raise ValidationError("A transaction with this data already exists")
    except OperationFailure as of:
        logger.error(f"Database operation failed in create_transaction: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to create transaction: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_transaction: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to create transaction: {str(e)}")


def get_transaction(db: Database, transaction_id: str, vendor_id: str) -> Transaction:
    """Retrieve a transaction by its ID.

    Args:
        db (Database): MongoDB database instance.
        transaction_id (str): ID of the transaction to retrieve.
        vendor_id (str): ID of the vendor requesting the transaction.

    Returns:
        Transaction: The requested transaction object.

    Raises:
        ValidationError: If transaction_id or vendor_id is invalid.
        NotFoundError: If transaction is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(transaction_id):
            raise ValidationError(f"Invalid transaction ID format: {transaction_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        transaction = db.transactions.find_one({"_id": ObjectId(transaction_id)})
        if not transaction:
            raise NotFoundError(f"Transaction with ID {transaction_id} not found")
        if transaction["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only view your own transactions")

        logger.info(f"Transaction retrieved: {transaction_id} for vendor: {vendor_id}")
        return Transaction(**transaction)
    except ValidationError as ve:
        logger.error(f"Validation error in get_transaction: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in get_transaction: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in get_transaction: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_transaction: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get transaction: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_transaction: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get transaction: {str(e)}")


def get_transactions_by_vendor(db: Database, vendor_id: str) -> list[Transaction]:
    """Retrieve all transactions for a specific vendor.

    Args:
        db (Database): MongoDB database instance.
        vendor_id (str): ID of the vendor to retrieve transactions for.

    Returns:
        list[Transaction]: List of transaction objects.

    Raises:
        ValidationError: If vendor_id is invalid.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        transactions = list(db.transactions.find({"vendor_id": vendor_id}))
        if not transactions:
            logger.debug(f"No transactions found for vendor_id: {vendor_id}")
            return []

        logger.info(f"Retrieved {len(transactions)} transactions for vendor_id: {vendor_id}")
        return [Transaction(**transaction) for transaction in transactions]
    except ValidationError as ve:
        logger.error(f"Validation error in get_transactions_by_vendor: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed in get_transactions_by_vendor: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to get transactions: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_transactions_by_vendor: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get transactions: {str(e)}")


def update_transaction(db: Database, transaction_id: str, vendor_id: str, update_data: dict) -> Transaction:
    """Update an existing transaction.

    Args:
        db (Database): MongoDB database instance.
        transaction_id (str): ID of the transaction to update.
        vendor_id (str): ID of the vendor updating the transaction.
        update_data (dict): Data to update in the transaction.

    Returns:
        Transaction: The updated transaction object.

    Raises:
        ValidationError: If transaction_id, vendor_id, or status is invalid.
        NotFoundError: If transaction is not found.
        UnauthorizedError: If vendor is not authorized.
        InternalServerError: For unexpected errors or database failures.
    """
    try:
        if not ObjectId.is_valid(transaction_id):
            raise ValidationError(f"Invalid transaction ID format: {transaction_id}")
        if not ObjectId.is_valid(vendor_id):
            raise ValidationError(f"Invalid vendor_id format: {vendor_id}")

        transaction = db.transactions.find_one({"_id": ObjectId(transaction_id)})
        if not transaction:
            raise NotFoundError(f"Transaction with ID {transaction_id} not found")
        if transaction["vendor_id"] != vendor_id:
            raise UnauthorizedError("You can only update your own transactions")

        if "status" in update_data and update_data["status"] not in ["pending", "completed", "failed"]:
            raise ValidationError("Invalid status value")

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = db.transactions.update_one({"_id": ObjectId(transaction_id)}, {"$set": update_data})
        if updated.matched_count == 0:
            raise InternalServerError(f"Failed to update transaction {transaction_id}")

        updated_transaction = db.transactions.find_one({"_id": ObjectId(transaction_id)})
        logger.info(f"Transaction updated: {transaction_id} by vendor: {vendor_id}")
        return Transaction(**updated_transaction)
    except ValidationError as ve:
        logger.error(f"Validation error in update_transaction: {ve.detail}")
        raise ve
    except NotFoundError as ne:
        logger.error(f"Not found error in update_transaction: {ne.detail}")
        raise ne
    except UnauthorizedError as ue:
        logger.error(f"Unauthorized error in update_transaction: {ue.detail}")
        raise ue
    except OperationFailure as of:
        logger.error(f"Database operation failed in update_transaction: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to update transaction: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error in update_transaction: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to update transaction: {str(e)}")

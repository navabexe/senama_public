# services/wallet.py
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError

from core.errors import NotFoundError, ValidationError, UnauthorizedError, InternalServerError
from core.utils.validation import validate_object_id
from domain.entities.transaction import Transaction
from domain.schemas.transaction import TransactionCreate, TransactionUpdate

logger = logging.getLogger(__name__)

class WalletService:
    def __init__(self, db: Database):
        """Initialize WalletService with a database instance."""
        self.db = db

    def create_transaction(self, vendor_id: str, transaction_data: Dict[str, Any]) -> Dict[str, str]:
        """Create a new transaction for a vendor and update wallet balance with atomic check.

        Args:
            vendor_id (str): ID of the vendor creating the transaction.
            transaction_data (Dict[str, Any]): Data for the transaction including amount, type, and optional description.

        Returns:
            Dict[str, str]: Dictionary containing the created transaction ID.

        Raises:
            ValidationError: If required fields are missing, invalid, or insufficient balance.
            NotFoundError: If vendor is not found.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(vendor_id, "vendor_id")
            transaction_create = TransactionCreate(**transaction_data)  # اعتبارسنجی با Pydantic
            transaction_data_validated = transaction_create.model_dump()

            vendor = self.db.vendors.find_one({"_id": ObjectId(vendor_id)})
            if not vendor:
                raise NotFoundError(f"Vendor with ID {vendor_id} not found")

            balance_change = transaction_data_validated["amount"] if transaction_data_validated["type"] == "deposit" else -transaction_data_validated["amount"]
            if transaction_data_validated["type"] == "withdrawal" and vendor["wallet_balance"] < transaction_data_validated["amount"]:
                raise ValidationError("Insufficient wallet balance for withdrawal")

            transaction_data_validated["vendor_id"] = vendor_id
            transaction_data_validated["status"] = "pending"  # وضعیت پیش‌فرض
            transaction = Transaction(**transaction_data_validated)

            with self.db.client.start_session() as session:
                with session.start_transaction():
                    # بررسی اتمی برای جلوگیری از تراکنش تکراری
                    query = {
                        "vendor_id": vendor_id,
                        "amount": transaction_data_validated["amount"],
                        "type": transaction_data_validated["type"],
                        "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=5)}  # بازه زمانی 5 دقیقه
                    }
                    existing_transaction = self.db.transactions.find_one(query, session=session)
                    if existing_transaction:
                        raise ValidationError(f"A similar transaction already exists for vendor {vendor_id} within the last 5 minutes")

                    result = self.db.transactions.insert_one(transaction.model_dump(exclude={"id"}), session=session)
                    transaction_id = str(result.inserted_id)

                    # به‌روزرسانی موجودی کیف‌پول به صورت اتمی
                    self.db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$inc": {"wallet_balance": balance_change}}, session=session)

            logger.info(f"Transaction created with ID: {transaction_id} for vendor: {vendor_id}")
            return {"id": transaction_id}
        except ValidationError as ve:
            logger.error(f"Validation error in create_transaction: {ve.detail}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error in create_transaction: {ne.detail}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database operation failed in create_transaction: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to create transaction: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in create_transaction: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to create transaction: {str(e)}")

    def get_transaction(self, transaction_id: str, vendor_id: str) -> Transaction:
        """Retrieve a transaction by its ID.

        Args:
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
            validate_object_id(transaction_id, "transaction_id")
            validate_object_id(vendor_id, "vendor_id")

            transaction = self.db.transactions.find_one({"_id": ObjectId(transaction_id)})
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

    def get_transactions_by_vendor(self, vendor_id: str) -> List[Transaction]:
        """Retrieve all transactions for a specific vendor.

        Args:
            vendor_id (str): ID of the vendor to retrieve transactions for.

        Returns:
            List[Transaction]: List of transaction objects.

        Raises:
            ValidationError: If vendor_id is invalid.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(vendor_id, "vendor_id")

            transactions = list(self.db.transactions.find({"vendor_id": vendor_id}))
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

    def update_transaction(self, transaction_id: str, vendor_id: str, update_data: Dict[str, Any]) -> Transaction:
        """Update an existing transaction.

        Args:
            transaction_id (str): ID of the transaction to update.
            vendor_id (str): ID of the vendor updating the transaction.
            update_data (Dict[str, Any]): Data to update in the transaction (e.g., status, description).

        Returns:
            Transaction: The updated transaction object.

        Raises:
            ValidationError: If transaction_id, vendor_id, or data is invalid.
            NotFoundError: If transaction is not found.
            UnauthorizedError: If vendor is not authorized.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(transaction_id, "transaction_id")
            validate_object_id(vendor_id, "vendor_id")
            transaction_update = TransactionUpdate(**update_data)  # اعتبارسنجی با Pydantic
            update_data_validated = transaction_update.model_dump(exclude_unset=True)

            transaction = self.db.transactions.find_one({"_id": ObjectId(transaction_id)})
            if not transaction:
                raise NotFoundError(f"Transaction with ID {transaction_id} not found")
            if transaction["vendor_id"] != vendor_id:
                raise UnauthorizedError("You can only update your own transactions")

            update_data_validated["updated_at"] = datetime.now(timezone.utc)
            updated = self.db.transactions.update_one({"_id": ObjectId(transaction_id)}, {"$set": update_data_validated})
            if updated.matched_count == 0:
                raise InternalServerError(f"Failed to update transaction {transaction_id}")

            updated_transaction = self.db.transactions.find_one({"_id": ObjectId(transaction_id)})
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

    def get_wallet_balance(self, vendor_id: str) -> Dict[str, float]:
        """Retrieve the current wallet balance for a vendor.

        Args:
            vendor_id (str): ID of the vendor to retrieve balance for.

        Returns:
            Dict[str, float]: Dictionary containing the vendor's wallet balance.

        Raises:
            ValidationError: If vendor_id is invalid.
            NotFoundError: If vendor is not found.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(vendor_id, "vendor_id")

            vendor = self.db.vendors.find_one({"_id": ObjectId(vendor_id)}, {"wallet_balance": 1})
            if not vendor:
                raise NotFoundError(f"Vendor with ID {vendor_id} not found")

            logger.info(f"Wallet balance retrieved for vendor: {vendor_id}")
            return {"balance": vendor.get("wallet_balance", 0.0)}
        except ValidationError as ve:
            logger.error(f"Validation error in get_wallet_balance: {ve.detail}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error in get_wallet_balance: {ne.detail}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database operation failed in get_wallet_balance: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to get wallet balance: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in get_wallet_balance: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to get wallet balance: {str(e)}")

    def delete_transaction(self, transaction_id: str, vendor_id: str) -> Dict[str, str]:
        """Delete a transaction and revert wallet balance with atomic check.

        Args:
            transaction_id (str): ID of the transaction to delete.
            vendor_id (str): ID of the vendor deleting the transaction.

        Returns:
            Dict[str, str]: Confirmation message of deletion.

        Raises:
            ValidationError: If transaction_id or vendor_id is invalid or status is not pending.
            NotFoundError: If transaction is not found.
            UnauthorizedError: If vendor is not authorized.
            InternalServerError: For unexpected errors or database failures.
        """
        try:
            validate_object_id(transaction_id, "transaction_id")
            validate_object_id(vendor_id, "vendor_id")

            transaction = self.db.transactions.find_one({"_id": ObjectId(transaction_id)})
            if not transaction:
                raise NotFoundError(f"Transaction with ID {transaction_id} not found")
            if transaction["vendor_id"] != vendor_id:
                raise UnauthorizedError("You can only delete your own transactions")
            if transaction["status"] != "pending":
                raise ValidationError("Only pending transactions can be deleted")

            with self.db.client.start_session() as session:
                with session.start_transaction():
                    # بازگرداندن تغییر موجودی کیف‌پول
                    balance_change = -transaction["amount"] if transaction["type"] == "deposit" else transaction["amount"]
                    self.db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$inc": {"wallet_balance": balance_change}}, session=session)
                    self.db.transactions.delete_one({"_id": ObjectId(transaction_id)}, session=session)

            logger.info(f"Transaction deleted: {transaction_id} by vendor: {vendor_id}")
            return {"message": f"Transaction {transaction_id} deleted successfully"}
        except ValidationError as ve:
            logger.error(f"Validation error in delete_transaction: {ve.detail}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error in delete_transaction: {ne.detail}")
            raise ne
        except UnauthorizedError as ue:
            logger.error(f"Unauthorized error in delete_transaction: {ue.detail}")
            raise ue
        except OperationFailure as of:
            logger.error(f"Database operation failed in delete_transaction: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to delete transaction: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in delete_transaction: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to delete transaction: {str(e)}")
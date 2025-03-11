# core/utils/pagination.py
import logging
from typing import List, Dict, Any

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator
from pymongo.collection import Collection
from pymongo.errors import OperationFailure

from core.errors import ValidationError, InternalServerError

logger = logging.getLogger(__name__)


class PaginationParams(BaseModel):
    """Parameters for pagination."""
    page: int = Field(1, ge=1, description="Page number (must be >= 1)")
    page_size: int = Field(10, ge=1, description="Number of items per page (must be >= 1)")

    @field_validator("page", "page_size")
    def ensure_positive(cls, value):
        if value < 1:
            raise ValueError("Value must be greater than or equal to 1")
        return value


class Pagination:
    """Class to handle pagination logic."""

    def __init__(self, page: int = 1, page_size: int = 10):
        """Initialize pagination with page and page_size.

        Args:
            page (int): Page number, defaults to 1.
            page_size (int): Items per page, defaults to 10.

        Raises:
            ValidationError: If page or page_size is invalid.
        """
        try:
            params = PaginationParams(page=page, page_size=page_size)
            self.page = params.page
            self.page_size = params.page_size
            self.skip = (self.page - 1) * self.page_size
        except ValueError as ve:
            logger.error(f"Validation error initializing pagination: {str(ve)}")
            raise ValidationError(f"Invalid pagination parameters: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error initializing pagination: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to initialize pagination: {str(e)}")

    def paginate(self, query: List[Any], total: int) -> Dict[str, Any]:
        """Paginate a list of results.

        Args:
            query (List[Any]): List of items to paginate.
            total (int): Total number of items.

        Returns:
            Dict[str, Any]: Paginated result with data, total, page, page_size, and total_pages.

        Raises:
            ValidationError: If query or total is invalid.
            InternalServerError: If pagination fails unexpectedly.
        """
        try:
            if not isinstance(query, list):
                raise ValidationError("Query must be a list")
            if not isinstance(total, int) or total < 0:
                raise ValidationError("Total must be a non-negative integer")

            paginated_data = query[self.skip:self.skip + self.page_size]
            return {
                "data": paginated_data,
                "total": total,
                "page": self.page,
                "page_size": self.page_size,
                "total_pages": (total + self.page_size - 1) // self.page_size
            }
        except ValidationError as ve:
            logger.error(f"Validation error in pagination: {ve.detail}")
            raise ve
        except IndexError as ie:
            logger.error(f"Index error in pagination: {str(ie)}", exc_info=True)
            raise InternalServerError(f"Failed to paginate results: Invalid index - {str(ie)}")
        except Exception as e:
            logger.error(f"Unexpected error in pagination: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to paginate results: {str(e)}")


def paginate_results(db_collection: Collection, filter: Dict[str, Any], page: int = 1, page_size: int = 10) -> Dict[
    str, Any]:
    """Paginate database query results.

    Args:
        db_collection (Collection): MongoDB collection to query.
        filter (Dict[str, Any]): Filter criteria for the query, with '_id' as string if present.
        page (int): Page number, defaults to 1.
        page_size (int): Items per page, defaults to 10.

    Returns:
        Dict[str, Any]: Paginated result with data, total, page, page_size, and total_pages.

    Raises:
        ValidationError: If filter, page, or page_size is invalid.
        InternalServerError: If database query fails.
    """
    try:
        if not isinstance(filter, dict):
            raise ValidationError("Filter must be a dictionary")
        if "_id" in filter and not ObjectId.is_valid(filter["_id"]):
            raise ValidationError(f"Invalid '_id' format in filter: {filter['_id']}")
        if "_id" in filter:
            filter["_id"] = ObjectId(filter["_id"])

        pagination = Pagination(page, page_size)
        total = db_collection.count_documents(filter)
        results = list(db_collection.find(filter).skip(pagination.skip).limit(pagination.page_size))
        return pagination.paginate(results, total)
    except ValidationError as ve:
        logger.error(f"Validation error paginating database results: {ve.detail}")
        raise ve
    except OperationFailure as of:
        logger.error(f"Database operation failed paginating results: {str(of)}", exc_info=True)
        raise InternalServerError(f"Failed to paginate database results: {str(of)}")
    except Exception as e:
        logger.error(f"Unexpected error paginating database results: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to paginate database results: {str(e)}")

# services/upload.py
import logging
import mimetypes
import os
from datetime import datetime, timezone
from typing import Dict

from bson import ObjectId
from fastapi import UploadFile
from pymongo.database import Database
from pymongo.errors import OperationFailure

from core.errors import ValidationError, InternalServerError, NotFoundError
from core.utils import db
from core.utils.validation import validate_object_id
from core.utils.db import DBHelper
from domain.schemas.upload import UploadMetadata

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

class UploadService:
    def __init__(cls, db: Database):
        """Initialize UploadService with a database instance and create upload directory if it doesn't exist."""
        cls.db_helper = DBHelper()
        cls.db = db
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)
            logger.info(f"Created upload directory: {UPLOAD_DIR}")

    async def upload_file(cls, user_id: str, file: UploadFile, entity_type: str, entity_id: str) -> Dict[str, str]:
        """Upload a file and associate it with a user, vendor, or product with atomic check.

        Args:
            user_id (str): ID of the user uploading the file.
            file (UploadFile): The file to upload.
            entity_type (str): Type of entity ('user', 'vendor', 'product').
            entity_id (str): ID of the entity to associate the file with.

        Returns:
            Dict[str, str]: Dictionary containing the uploaded file URL.

        Raises:
            ValidationError: If file size, type, or entity details are invalid.
            NotFoundError: If entity is not found.
            InternalServerError: For unexpected errors or file system failures.
        """
        try:
            validate_object_id(user_id, "user_id")
            validate_object_id(entity_id, "entity_id")
            upload_metadata = UploadMetadata(user_id=user_id, entity_type=entity_type, entity_id=entity_id)

            file_size = file.size
            if file_size is None or file_size > MAX_FILE_SIZE:
                raise ValidationError(f"File size exceeds maximum limit of {MAX_FILE_SIZE / (1024 * 1024)} MB")

            allowed_types = ["image/jpeg", "image/png", "video/mp4"]
            if file.content_type not in allowed_types:
                raise ValidationError(f"File type {file.content_type} not allowed. Allowed types: {allowed_types}")

            content = await file.read()
            mime_type = mimetypes.guess_type(file.filename)[0] or file.content_type
            if mime_type not in allowed_types:
                raise ValidationError(f"Invalid file content type: {mime_type}. Allowed types: {allowed_types}")
            await file.seek(0)

            collection_name = entity_type + "s"
            entity = cls.db_helper.find_one(collection_name, {"_id": ObjectId(entity_id)})
            if not entity:
                raise NotFoundError(f"{entity_type.capitalize()} with ID {entity_id} not found")
            if entity_type != "user" and str(entity["_id"]) != user_id and entity.get("vendor_id") != user_id:
                raise ValidationError("You can only upload files for your own entity")

            # ذخیره فایل و به‌روزرسانی دیتابیس به صورت اتمی
            file_extension = file.filename.split(".")[-1]
            file_name = f"{entity_type}_{entity_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, file_name)
            file_url = f"/{UPLOAD_DIR}/{file_name}"

            with db.client.start_session() as session:
                with session.start_transaction():
                    # بررسی اتمی برای جلوگیری از آپلود همزمان (اختیاری، بر اساس URL)
                    existing_url = cls.db_helper.find_one(collection_name, {f"{entity_type == 'product' and 'images' or 'avatar_urls'}": file_url}, session=session)
                    if existing_url:
                        raise ValidationError(f"A file with URL {file_url} already exists for this entity")

                    # ذخیره فایل
                    with open(file_path, "wb") as buffer:
                        buffer.write(await file.read())

                    # به‌روزرسانی دیتابیس
                    update_field = "avatar_urls" if entity_type in ["user", "vendor"] else "images"
                    current_urls = entity.get(update_field, [])
                    updated = cls.db_helper.update_one(
                        collection_name,
                        {"_id": ObjectId(entity_id)},
                        {update_field: current_urls + [file_url]},
                        session=session
                    )
                    if not updated:
                        os.remove(file_path)  # Rollback file if database update fails
                        raise InternalServerError(f"Failed to update {entity_type} with file URL")

            logger.info(f"File uploaded: {file_path} for {entity_type} {entity_id} by user {user_id}, size: {file_size} bytes")
            return {"file_url": file_url}
        except ValidationError as ve:
            logger.error(f"Validation error in upload_file: {ve.detail}, filename: {file.filename}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Not found error in upload_file: {ne.detail}")
            raise ne
        except OperationFailure as of:
            logger.error(f"Database operation failed in upload_file: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to upload file: {str(of)}")
        except Exception as e:
            logger.error(f"Unexpected error in upload_file: {str(e)}, filename: {file.filename}", exc_info=True)
            raise InternalServerError(f"Failed to upload file: {str(e)}")

    def cleanup_unused_files(cls) -> Dict[str, str]:
        """Clean up unused files from the upload directory.

        Returns:
            Dict[str, str]: Confirmation message with count of deleted files.

        Raises:
            InternalServerError: For unexpected errors or file system failures.
        """
        try:
            used_files = set()
            for collection in ["users", "vendors", "products"]:
                for entity in cls.db[collection].find():
                    urls = entity.get("avatar_urls", []) + entity.get("images", [])
                    used_files.update(urls)

            deleted_count = 0
            for file_name in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, file_name)
                file_url = f"/{UPLOAD_DIR}/{file_name}"
                if file_url not in used_files and os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    logger.debug(f"Deleted unused file: {file_path}")

            logger.info(f"Cleaned up {deleted_count} unused files from {UPLOAD_DIR}")
            return {"message": f"Cleaned up {deleted_count} unused files"}
        except OperationFailure as of:
            logger.error(f"Database operation failed in cleanup_unused_files: {str(of)}", exc_info=True)
            raise InternalServerError(f"Failed to clean up unused files: {str(of)}")
        except OSError as ose:
            logger.error(f"File system error in cleanup_unused_files: {str(ose)}", exc_info=True)
            raise InternalServerError(f"Failed to clean up unused files: {str(ose)}")
        except Exception as e:
            logger.error(f"Unexpected error in cleanup_unused_files: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to clean up unused files: {str(e)}")
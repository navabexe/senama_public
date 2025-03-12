# infrastructure/external/file_storage.py
import logging
import os
from typing import Optional

from fastapi import UploadFile

from core.errors import InternalServerError

logger = logging.getLogger(__name__)

class FileStorage:
    """Simple file storage utility for handling uploads."""

    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            logger.info(f"Created upload directory: {upload_dir}")

    async def save_file(self, file: UploadFile, filename: Optional[str] = None) -> str:
        """Save an uploaded file to the storage directory."""
        try:
            filename = filename or file.filename
            if not filename:
                raise ValueError("Filename cannot be empty")
            file_path = os.path.join(self.upload_dir, filename)

            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            logger.info(f"File saved: {file_path}")
            return file_path
        except ValueError as ve:
            logger.error(f"Invalid filename: {str(ve)}")
            raise InternalServerError(f"Invalid filename: {str(ve)}")
        except Exception as e:
            logger.error(f"Failed to save file: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to save file: {str(e)}")

    def delete_file(self, file_path: str) -> None:
        """Delete a file from the storage directory."""
        try:
            if not file_path or not isinstance(file_path, str):
                raise ValueError("File path must be a non-empty string")
            full_path = os.path.join(self.upload_dir, file_path) if not os.path.isabs(file_path) else file_path
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"File deleted: {full_path}")
            else:
                logger.warning(f"File not found: {full_path}")
        except ValueError as ve:
            logger.error(f"Invalid file path: {str(ve)}")
            raise InternalServerError(f"Invalid file path: {str(ve)}")
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to delete file: {str(e)}")

file_storage = FileStorage()
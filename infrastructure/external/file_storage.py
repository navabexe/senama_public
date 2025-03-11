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
            if filename is None:
                filename = file.filename
            file_path = os.path.join(self.upload_dir, filename)

            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            logger.info(f"File saved successfully: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save file: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to save file: {str(e)}")

    def delete_file(self, file_path: str) -> None:
        """Delete a file from the storage directory."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted successfully: {file_path}")
            else:
                logger.warning(f"File not found for deletion: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}", exc_info=True)
            raise InternalServerError(f"Failed to delete file: {str(e)}")


file_storage = FileStorage()

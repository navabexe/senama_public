# core/logging/setup.py
import logging
import logging.config

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.errors import InternalServerError


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests and outgoing responses."""

    async def dispatch(self, request: Request, call_next):
        """Log request and response details.

        Args:
            request (Request): The incoming HTTP request.
            call_next: The next middleware or endpoint to process the request.

        Returns:
            Response: The HTTP response after processing.

        Raises:
            InternalServerError: If an unexpected error occurs during request processing.
        """
        logger = logging.getLogger("senama_app")
        try:
            logger.info(
                f"Request: {request.method} {request.url.path} "
                f"from {request.client.host} "
                f"headers={dict(request.headers)}"
            )
            response = await call_next(request)
            logger.info(
                f"Response: {request.method} {request.url.path} "
                f"status={response.status_code}"
            )
            return response
        except ValueError as ve:
            logger.error(f"ValueError in request processing: {str(ve)}", exc_info=True)
            raise InternalServerError(f"Invalid request data: {str(ve)}")
        except RuntimeError as re:
            logger.error(f"RuntimeError in request processing: {str(re)}", exc_info=True)
            raise InternalServerError(f"Request processing failed: {str(re)}")
        except Exception as e:
            logger.error(f"Unexpected error in request processing: {str(e)}", exc_info=True)
            raise InternalServerError(f"Internal server error: {str(e)}")


def setup_logging(app: FastAPI) -> None:
    """Set up logging configuration for the application.

    Args:
        app (FastAPI): The FastAPI application instance to configure logging for.

    Raises:
        InternalServerError: If logging setup fails due to configuration errors.
    """
    try:
        LOGGING_CONFIG = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": "app.log",
                    "level": "DEBUG",
                    "formatter": "default",
                },
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "default",
                },
            },
            "loggers": {
                "senama_app": {
                    "level": "DEBUG",
                    "handlers": ["file", "console"],
                    "propagate": False,
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["console"],
            },
        }

        logging.config.model_dumpConfig(LOGGING_CONFIG)

        app.add_middleware(LoggingMiddleware)

        logger = logging.getLogger("senama_app")
        logger.info("Logging setup completed successfully")

    except ValueError as ve:
        error_msg = f"Invalid logging configuration: {str(ve)}"
        logging.getLogger().error(error_msg, exc_info=True)
        raise InternalServerError(error_msg)
    except FileNotFoundError as fnf:
        error_msg = f"Log file path error: {str(fnf)}"
        logging.getLogger().error(error_msg, exc_info=True)
        raise InternalServerError(error_msg)
    except PermissionError as pe:
        error_msg = f"Permission denied setting up logging: {str(pe)}"
        logging.getLogger().error(error_msg, exc_info=True)
        raise InternalServerError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error setting up logging: {str(e)}"
        logging.getLogger().error(error_msg, exc_info=True)
        raise InternalServerError(error_msg)

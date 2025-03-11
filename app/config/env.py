# app/config/env.py
import logging
import os
from typing import Optional

from dotenv import load_dotenv

from core.errors import ValidationError

logger = logging.getLogger(__name__)

load_dotenv()


def get_env_var(name: str, default: Optional[str] = None) -> str:
    """Retrieve an environment variable with validation.

    Args:
        name (str): Name of the environment variable to retrieve.
        default (Optional[str]): Default value if the variable is not set. Defaults to None.

    Returns:
        str: The value of the environment variable.

    Raises:
        ValidationError: If the environment variable is not set and no default is provided.
    """
    value = os.getenv(name, default)
    if value is None:
        logger.error(f"Environment variable '{name}' is not set and no default provided")
        raise ValidationError(f"Environment variable '{name}' is required but not set")
    if not isinstance(value, str):
        logger.warning(f"Environment variable '{name}' is not a string: {value}")
        value = str(value)
    logger.debug(f"Retrieved environment variable: {name} = {value}")
    return value

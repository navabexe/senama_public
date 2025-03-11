# app/config/settings.py
import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.env import get_env_var

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    MONGO_URI: str = Field(description="MongoDB connection URI")
    MONGO_DB: str = Field(description="MongoDB database name")
    SECRET_KEY: str = Field(description="Secret key for JWT encoding")
    REFRESH_SECRET_KEY: str = Field(description="Secret key for refresh token encoding")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, ge=1, description="Access token expiration time in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, ge=1, description="Refresh token expiration time in days")
    OTP_EXPIRE_MINUTES: int = Field(5, ge=1, description="OTP expiration time in minutes")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid"
    )

    def __init__(self, **values):
        """Initialize settings and log the loaded values."""
        super().__init__(**values)
        logger.info("Settings initialized successfully")
        logger.debug(f"Loaded settings: MONGO_URI={self.MONGO_URI}, MONGO_DB={self.MONGO_DB}, "
                     f"ACCESS_TOKEN_EXPIRE_MINUTES={self.ACCESS_TOKEN_EXPIRE_MINUTES}, "
                     f"REFRESH_TOKEN_EXPIRE_DAYS={self.REFRESH_TOKEN_EXPIRE_DAYS}, "
                     f"OTP_EXPIRE_MINUTES={self.OTP_EXPIRE_MINUTES}")


def load_settings() -> Settings:
    """Load settings with environment variable validation."""
    try:
        settings = Settings(
            MONGO_URI=get_env_var("MONGO_URI"),
            MONGO_DB=get_env_var("MONGO_DB"),
            SECRET_KEY=get_env_var("SECRET_KEY"),
            REFRESH_SECRET_KEY=get_env_var("REFRESH_SECRET_KEY")
        )
        return settings
    except ValueError as ve:
        logger.error(f"Validation error loading settings: {str(ve)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading settings: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to load settings: {str(e)}")


settings = load_settings()

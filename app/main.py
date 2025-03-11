# app/main.py
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from pymongo.errors import OperationFailure, NetworkTimeout

from app.middleware.rate_limit import setup_rate_limit
from core.logging.setup import setup_logging, LoggingMiddleware
from infrastructure.database.client import get_db
from infrastructure.database.indexes import create_indexes
from routes.v1 import (
    auth, users, vendors, products, stories, orders, business_categories,
    product_categories, notifications, wallet, collaborations, blocked_users,
    advertisements, reports, sessions, admin, upload
)
from services.upload import UploadService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Senama Marketplace API",
    description="API for managing vendors, users, products, and more in a marketplace platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


def initialize_app():
    """Initialize application components."""
    try:
        setup_logging(app)
        logger.info("Logging setup completed")

        setup_rate_limit(app)
        logger.info("Rate limiting setup completed")
        app.add_middleware(LoggingMiddleware)

        try:
            create_indexes()
            logger.info("Database indexes created successfully")
        except OperationFailure as of:
            logger.error(f"Failed to create database indexes: {str(of)}", exc_info=True)
            raise RuntimeError(f"Database index creation failed: {str(of)}")
        except NetworkTimeout as nt:
            logger.error(f"Network timeout creating indexes: {str(nt)}", exc_info=True)
            raise RuntimeError(f"Database connection timeout: {str(nt)}")

        db = get_db()
        upload_service = UploadService(db)
        scheduler = AsyncIOScheduler()
        scheduler.add_job(upload_service.cleanup_unused_files, 'interval', hours=24)
        scheduler.start()
        logger.info("Scheduler started for cleanup tasks")

    except RuntimeError as re:
        logger.critical(f"Application initialization failed: {str(re)}", exc_info=True)
        raise
    except Exception as e:
        logger.critical(f"Unexpected error during initialization: {str(e)}", exc_info=True)
        raise RuntimeError(f"Unexpected initialization error: {str(e)}")


@app.get("/", summary="Root endpoint", description="Returns a welcome message")
async def root():
    return {"message": "Welcome to Senama Marketplace API"}


app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"])
app.include_router(vendors.router, prefix="/v1/vendors", tags=["Vendors"])
app.include_router(products.router, prefix="/v1/products", tags=["Products"])
app.include_router(stories.router, prefix="/v1/stories", tags=["Stories"])
app.include_router(orders.router, prefix="/v1/orders", tags=["Orders"])
app.include_router(business_categories.router, prefix="/v1/business-categories", tags=["Business Categories"])
app.include_router(product_categories.router, prefix="/v1/product-categories", tags=["Product Categories"])
app.include_router(notifications.router, prefix="/v1/notifications", tags=["Notifications"])
app.include_router(wallet.router, prefix="/v1/wallet", tags=["Wallet"])
app.include_router(collaborations.router, prefix="/v1/collaborations", tags=["Collaborations"])
app.include_router(blocked_users.router, prefix="/v1/blocked-users", tags=["Blocked Users"])
app.include_router(advertisements.router, prefix="/v1/advertisements", tags=["Advertisements"])
app.include_router(reports.router, prefix="/v1/reports", tags=["Reports"])
app.include_router(sessions.router, prefix="/v1/sessions", tags=["Sessions"])
app.include_router(admin.router, prefix="/v1/admin", tags=["Admin"])
app.include_router(upload.router, prefix="/v1/upload", tags=["Upload"])

if __name__ == "__main__":
    initialize_app()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

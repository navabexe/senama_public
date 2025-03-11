# add_admin.py
import logging
from datetime import datetime, timezone

from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_admin():
    try:
        # اتصال به دیتابیس
        client = MongoClient("mongodb://localhost:27017")
        db = client["senama_db"]

        # اطلاعات ادمین
        admin_data = {
            "phone": "+989123456789",
            "first_name": "Admin",
            "last_name": "User",
            "roles": ["admin"],
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "avatar_urls": [],
            "phones": ["+989123456789"],
            "bio": "Admin account",
            "birthdate": None,
            "gender": "male",
            "languages": ["fa", "en"],
            "following_vendor_ids": []
        }

        # اضافه کردن ادمین
        admin_result = db.users.insert_one(admin_data)
        admin_id = admin_result.inserted_id
        logger.info(f"Admin added with ID: {admin_id}")

        # دسته‌بندی‌های کسب‌وکار پیش‌فرض
        business_categories = [
            {
                "name": "Food",
                "description": "Food and beverage businesses",
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "name": "Fashion",
                "description": "Clothing and accessories",
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "name": "Electronics",
                "description": "Electronic gadgets and appliances",
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]

        # اضافه کردن دسته‌بندی‌های کسب‌وکار
        business_category_ids = {}
        for category in business_categories:
            result = db.business_categories.insert_one(category)
            business_category_ids[category["name"]] = result.inserted_id
            logger.info(f"Business category '{category['name']}' added with ID: {result.inserted_id}")

        # دسته‌بندی‌های محصول پیش‌فرض برای هر کسب‌وکار
        product_categories = {
            "Food": [
                {
                    "name": "Beverages",
                    "description": "Drinks and beverages",
                    "business_category_id": business_category_ids["Food"],
                    "status": "active",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                },
                {
                    "name": "Snacks",
                    "description": "Light meals and snacks",
                    "business_category_id": business_category_ids["Food"],
                    "status": "active",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            ],
            "Fashion": [
                {
                    "name": "Clothing",
                    "description": "Men and women clothing",
                    "business_category_id": business_category_ids["Fashion"],
                    "status": "active",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                },
                {
                    "name": "Accessories",
                    "description": "Jewelry and bags",
                    "business_category_id": business_category_ids["Fashion"],
                    "status": "active",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            ],
            "Electronics": [
                {
                    "name": "Gadgets",
                    "description": "Smartphones and wearables",
                    "business_category_id": business_category_ids["Electronics"],
                    "status": "active",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                },
                {
                    "name": "Appliances",
                    "description": "Home appliances",
                    "business_category_id": business_category_ids["Electronics"],
                    "status": "active",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            ]
        }

        # اضافه کردن دسته‌بندی‌های محصول
        for business_name, categories in product_categories.items():
            for category in categories:
                result = db.product_categories.insert_one(category)
                logger.info(
                    f"Product category '{category['name']}' added with ID: {result.inserted_id} under '{business_name}'")

        logger.info("Admin and default categories added successfully!")

    except Exception as e:
        logger.error(f"Failed to add admin or categories: {str(e)}")
        raise


if __name__ == "__main__":
    add_admin()

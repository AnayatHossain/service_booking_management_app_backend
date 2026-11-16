import re
from bson import ObjectId
from typing import Optional, List
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.helpers import format_mongo_doc, format_mongo_docs


async def list_services(
    db: AsyncIOMotorDatabase,
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_featured: Optional[bool] = None,
    limit: int = 50
) -> List[dict]:
    filter_query: dict = {"is_active": {"$ne": False}}

    if search and search.strip():
        regex_pattern = re.compile(re.escape(search.strip()), re.IGNORECASE)
        filter_query["$or"] = [
            {"name": {"$regex": regex_pattern}},
            {"description": {"$regex": regex_pattern}},
            {"category": {"$regex": regex_pattern}}
        ]

    if category and category.strip() and category.strip().lower() != "all":
        filter_query["category"] = {"$regex": f"^{re.escape(category.strip())}$", "$options": "i"}

    if is_featured is not None:
        filter_query["is_featured"] = is_featured

    # Return lightweight list projection to prevent overloading server and network
    cursor = db.services.find(
        filter_query,
        projection={
            "name": 1,
            "category": 1,
            "price": 1,
            "duration_minutes": 1,
            "image_url": 1,
            "is_featured": 1,
            "rating": 1,
            "total_reviews": 1,
            "description": 1,
        }
    ).sort("is_featured", -1).limit(limit)
    services = await cursor.to_list(length=limit)
    return format_mongo_docs(services)


async def get_service_details(db: AsyncIOMotorDatabase, service_id: str) -> dict:
    try:
        oid = ObjectId(service_id)
        service = await db.services.find_one({"_id": oid})
    except Exception:
        service = await db.services.find_one({"id": service_id})

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found."
        )

    formatted = format_mongo_doc(service)
    # Ensure rich detail fields are populated
    if "includes" not in formatted or not formatted["includes"]:
        duration = formatted.get("duration_minutes", 45)
        formatted["includes"] = [
            "Vetted & background checked professionals",
            f"{duration} mins comprehensive servicing",
            "Full satisfaction guarantee with free rework",
            "24/7 dedicated in-app support & easy cancel"
        ]
    if "available_days" not in formatted or not formatted["available_days"]:
        formatted["available_days"] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    if "time_slots" not in formatted or not formatted["time_slots"]:
        formatted["time_slots"] = [
            "09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM",
            "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
        ]
    return formatted


async def list_categories(db: AsyncIOMotorDatabase) -> List[str]:
    categories = await db.services.distinct("category", {"is_active": {"$ne": False}})
    return ["All"] + sorted([c for c in categories if c])

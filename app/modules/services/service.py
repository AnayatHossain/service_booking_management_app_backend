import re
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.helpers import format_mongo_doc, format_mongo_docs


async def list_services(
    db: AsyncIOMotorDatabase,
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_featured: Optional[bool] = None,
    sort_by: Optional[str] = None,
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

    # Determine sort order
    sort_criteria = [("is_featured", -1), ("rating", -1), ("total_reviews", -1)]
    if sort_by:
        s = sort_by.strip().lower()
        if s in ["price_low_high", "price_asc", "low_to_high"]:
            sort_criteria = [("price", 1)]
        elif s in ["price_high_low", "price_desc", "high_to_low"]:
            sort_criteria = [("price", -1)]
        elif s in ["rating_high", "highest_rated", "rating", "rating_desc"]:
            sort_criteria = [("rating", -1), ("total_reviews", -1)]
        elif s in ["recommended", "default"]:
            sort_criteria = [("is_featured", -1), ("rating", -1), ("total_reviews", -1)]

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
            "provider_id": 1,
            "provider_name": 1,
            "includes": 1,
            "available_days": 1,
            "time_slots": 1,
        }
    ).sort(sort_criteria).limit(limit)
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


async def update_service(
    db: AsyncIOMotorDatabase,
    service_id: str,
    update_data: dict,
    provider_id: Optional[str] = None
) -> dict:
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

    now = datetime.now(timezone.utc).isoformat()
    clean_data = {k: v for k, v in update_data.items() if v is not None}
    clean_data["updated_at"] = now

    updated = await db.services.find_one_and_update(
        {"_id": service["_id"]},
        {"$set": clean_data},
        return_document=True
    )

    s_id_str = str(service["_id"])
    match_service_ids = [s_id_str, service_id]

    # Synchronize updated image_url across appointments and notifications
    if "image_url" in clean_data and clean_data["image_url"]:
        new_img = clean_data["image_url"]
        await db.appointments.update_many(
            {"$or": [{"service_id": {"$in": match_service_ids}}, {"service_name": service.get("name")}]},
            {"$set": {"service_image": new_img, "updated_at": now}}
        )
        await db.notifications.update_many(
            {"$or": [{"service_id": {"$in": match_service_ids}}, {"service_name": service.get("name")}]},
            {"$set": {"service_image": new_img, "updated_at": now}}
        )

    # Synchronize updated name across appointments and notifications
    if "name" in clean_data and clean_data["name"]:
        new_name = clean_data["name"]
        await db.appointments.update_many(
            {"service_id": {"$in": match_service_ids}},
            {"$set": {"service_name": new_name, "updated_at": now}}
        )
        await db.notifications.update_many(
            {"service_id": {"$in": match_service_ids}},
            {"$set": {"service_name": new_name, "updated_at": now}}
        )

    return format_mongo_doc(updated)


async def delete_service(
    db: AsyncIOMotorDatabase,
    service_id: str,
    provider_id: Optional[str] = None
) -> bool:
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

    await db.services.delete_one({"_id": service["_id"]})
    return True

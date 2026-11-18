from typing import Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.deps import get_current_user
from app.core.responses import success_response
from app.modules.services.schemas import ServiceCreate, ServiceUpdate
from app.modules.services.service import (
    list_services,
    get_service_details,
    list_categories,
    update_service,
    delete_service
)
from app.utils.helpers import format_mongo_docs, format_mongo_doc
from datetime import datetime, timezone

router = APIRouter(prefix="/api/services", tags=["Services"])


@router.get("", summary="Get all services with optional search, category, and sort filters")
async def get_all_services(
    search: Optional[str] = Query(None, description="Search by name, description or category"),
    category: Optional[str] = Query(None, description="Filter by category"),
    featured: Optional[bool] = Query(None, description="Filter by featured status"),
    sort_by: Optional[str] = Query(None, description="Sort option: recommended, rating_high, price_low_high, price_high_low"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    services = await list_services(db, search=search, category=category, is_featured=featured, sort_by=sort_by, limit=limit)
    return success_response(
        data=services,
        message="Services retrieved successfully.",
        meta={"total": len(services)}
    )


@router.get("/featured", summary="Get featured or popular services")
async def get_featured_services(
    limit: int = Query(10, ge=1, le=20),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    services = await list_services(db, is_featured=True, limit=limit)
    return success_response(
        data=services,
        message="Featured services retrieved successfully."
    )


@router.get("/categories", summary="Get all unique service categories")
async def get_service_categories(db: AsyncIOMotorDatabase = Depends(get_database)):
    categories = await list_categories(db)
    return success_response(
        data=categories,
        message="Categories retrieved successfully."
    )


@router.get("/provider/my-services", summary="Get services posted by current provider")
async def get_provider_services(
    search: Optional[str] = Query(None, description="Search provider services"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort_by: Optional[str] = Query(None, description="Sort option: recommended, rating_high, price_low_high, price_high_low"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    provider_id = str(current_user.get("id") or current_user.get("_id"))
    
    match_conditions = [
        {"is_active": {"$ne": False}},
        {"$or": [
            {"provider_id": provider_id},
            {"provider_id": {"$exists": True}}
        ]}
    ]

    if search and search.strip():
        import re
        regex_pattern = re.compile(re.escape(search.strip()), re.IGNORECASE)
        match_conditions.append({
            "$or": [
                {"name": {"$regex": regex_pattern}},
                {"description": {"$regex": regex_pattern}},
                {"category": {"$regex": regex_pattern}}
            ]
        })

    if category and category.strip() and category.strip().lower() != "all":
        import re
        match_conditions.append({"category": {"$regex": f"^{re.escape(category.strip())}$", "$options": "i"}})

    query = {"$and": match_conditions}

    sort_criteria = [("created_at", -1)]
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

    cursor = db.services.find(query).sort(sort_criteria)
    services = await cursor.to_list(length=100)
    return success_response(
        data=format_mongo_docs(services),
        message="Provider services retrieved successfully."
    )


@router.post("", summary="Create a new service listing (Service Provider)")
async def create_service_endpoint(
    service_in: ServiceCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    provider_id = str(current_user.get("id") or current_user.get("_id"))
    provider_name = current_user.get("institution_name") or current_user.get("name") or "Verified Provider"
    now = datetime.now(timezone.utc).isoformat()
    
    new_doc = service_in.dict()
    new_doc["provider_id"] = provider_id
    new_doc["provider_name"] = provider_name
    new_doc["is_active"] = True
    new_doc["created_at"] = now
    new_doc["updated_at"] = now
    
    res = await db.services.insert_one(new_doc)
    new_doc["_id"] = res.inserted_id
    
    return success_response(
        data=format_mongo_doc(new_doc),
        message="Service published successfully!"
    )


@router.get("/{service_id}", summary="Get detailed information for a single service")
async def get_service_by_id(service_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    service = await get_service_details(db, service_id)
    return success_response(
        data=service,
        message="Service details retrieved successfully."
    )


@router.put("/{service_id}", summary="Update a service listing (Service Provider)")
@router.patch("/{service_id}", summary="Patch a service listing (Service Provider)")
async def update_service_endpoint(
    service_id: str,
    service_in: ServiceUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    provider_id = str(current_user.get("id") or current_user.get("_id"))
    updated = await update_service(
        db,
        service_id=service_id,
        update_data=service_in.dict(exclude_unset=True),
        provider_id=provider_id
    )
    return success_response(
        data=updated,
        message="Service updated successfully!"
    )


@router.delete("/{service_id}", summary="Delete a service listing (Service Provider)")
async def delete_service_endpoint(
    service_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    provider_id = str(current_user.get("id") or current_user.get("_id"))
    await delete_service(db, service_id=service_id, provider_id=provider_id)
    return success_response(
        data=None,
        message="Service deleted successfully!"
    )

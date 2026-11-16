from typing import Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.responses import success_response
from app.modules.services.service import list_services, get_service_details, list_categories

router = APIRouter(prefix="/api/services", tags=["Services"])


@router.get("", summary="Get all services with optional search and category filters")
async def get_all_services(
    search: Optional[str] = Query(None, description="Search by name, description or category"),
    category: Optional[str] = Query(None, description="Filter by category"),
    featured: Optional[bool] = Query(None, description="Filter by featured status"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    services = await list_services(db, search=search, category=category, is_featured=featured, limit=limit)
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


@router.get("/{service_id}", summary="Get detailed information for a single service")
async def get_service_by_id(service_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    service = await get_service_details(db, service_id)
    return success_response(
        data=service,
        message="Service details retrieved successfully."
    )

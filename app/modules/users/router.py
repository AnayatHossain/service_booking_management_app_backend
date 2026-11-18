from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.deps import get_current_user
from app.core.responses import success_response
from app.modules.users.schemas import UpdateProfileRequest, ChangePasswordRequest
from app.modules.users.service import (
    update_user_profile,
    change_user_password,
    delete_user_account,
)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/profile", summary="Get personal profile with stats")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user.get("id") or current_user.get("_id"))
    user_role = str(current_user.get("role", "customer")).lower()
    is_provider = user_role in ["provider", "service_provider"]

    if is_provider:
        apt_filter = {"$or": [{"provider_id": user_id}, {"user_id": user_id}]}
    else:
        apt_filter = {"user_id": user_id}

    total_bookings = await db.appointments.count_documents(apt_filter)
    active_bookings = await db.appointments.count_documents({
        **apt_filter,
        "status": {"$in": ["Pending", "Confirmed"]}
    })
    completed_bookings = await db.appointments.count_documents({
        **apt_filter,
        "status": "Completed"
    })
    cancelled_bookings = await db.appointments.count_documents({
        **apt_filter,
        "status": "Cancelled"
    })

    enriched = dict(current_user)
    enriched["total_bookings"] = total_bookings
    enriched["active_bookings"] = active_bookings
    enriched["completed_bookings"] = completed_bookings
    enriched["cancelled_bookings"] = cancelled_bookings

    org = current_user.get("organization_name") or current_user.get("institution_name") or ""
    enriched["organization_name"] = org
    enriched["institution_name"] = org

    return success_response(
        data=enriched,
        message="Profile fetched successfully."
    )


@router.put("/profile", summary="Update personal profile")
async def update_profile(
    req: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    updated = await update_user_profile(db, current_user["id"], req)
    return success_response(
        data=updated,
        message="Profile updated successfully."
    )


@router.post("/change-password", summary="Change current password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    await change_user_password(db, current_user["id"], req)
    return success_response(
        data=None,
        message="Password changed successfully."
    )


@router.delete("/profile", summary="Permanently delete account and all data")
async def delete_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user.get("id") or current_user.get("_id"))
    await delete_user_account(db, user_id)
    return success_response(
        data=None,
        message="Your account and all associated data have been permanently deleted."
    )

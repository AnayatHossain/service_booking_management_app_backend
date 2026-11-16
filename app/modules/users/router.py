from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.deps import get_current_user
from app.core.responses import success_response
from app.modules.users.schemas import UpdateProfileRequest, ChangePasswordRequest
from app.modules.users.service import update_user_profile, change_user_password

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/profile", summary="Get personal profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return success_response(
        data=current_user,
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

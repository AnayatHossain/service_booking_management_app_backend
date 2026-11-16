from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import hash_password, check_password
from app.modules.users.schemas import UpdateProfileRequest, ChangePasswordRequest
from app.utils.helpers import format_mongo_doc


async def update_user_profile(
    db: AsyncIOMotorDatabase,
    user_id: str,
    req: UpdateProfileRequest
) -> dict:
    update_data = {}
    if req.name is not None and req.name.strip():
        update_data["name"] = req.name.strip()
    if req.phone is not None:
        update_data["phone"] = req.phone.strip()
    if req.avatar_url is not None:
        update_data["avatar_url"] = req.avatar_url.strip()

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update."
        )

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        oid = ObjectId(user_id)
    except Exception:
        oid = user_id

    result = await db.users.find_one_and_update(
        {"_id": oid},
        {"$set": update_data},
        return_document=True
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    formatted = format_mongo_doc(result)
    formatted.pop("password", None)
    return formatted


async def change_user_password(
    db: AsyncIOMotorDatabase,
    user_id: str,
    req: ChangePasswordRequest
) -> bool:
    try:
        oid = ObjectId(user_id)
    except Exception:
        oid = user_id

    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if not check_password(req.current_password, user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password does not match."
        )

    new_hash = hash_password(req.new_password)
    now = datetime.now(timezone.utc).isoformat()

    await db.users.update_one(
        {"_id": oid},
        {"$set": {"password": new_hash, "updated_at": now}}
    )
    return True

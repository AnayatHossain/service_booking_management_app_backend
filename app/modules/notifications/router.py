from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.database import db
from app.core.responses import success_response, error_response
from app.utils.helpers import serialize_mongo_doc

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationItem(BaseModel):
    id: str
    title: str
    message: str
    type: str  # 'booking', 'promo', 'system', 'reminder'
    is_read: bool = False
    created_at: str


@router.get("", summary="Get all notifications for authenticated user")
async def get_user_notifications(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    cursor = db.get_collection("notifications").find({"user_id": user_id}).sort("created_at", -1)
    notifications = []
    async for doc in cursor:
        notifications.append(serialize_mongo_doc(doc))

    # If no notifications exist yet, generate friendly initial welcome & tips notifications
    if not notifications:
        default_items = [
            {
                "user_id": user_id,
                "title": "Welcome to Service Booking! 🎉",
                "message": "Explore premium home cleaning, repairs, salon, and plumbing services at your fingertips.",
                "type": "system",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "user_id": user_id,
                "title": "20% Discount Available 🔥",
                "message": "Book your first Deep Cleaning or AC Service today and get up to 20% instant discount.",
                "type": "promo",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "user_id": user_id,
                "title": "AI Assistant Ready 🤖",
                "message": "Need help choosing the right service? Chat with our Gemini AI Service Assistant anytime!",
                "type": "reminder",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        res = await db.get_collection("notifications").insert_many(default_items)
        cursor2 = db.get_collection("notifications").find({"user_id": user_id}).sort("created_at", -1)
        async for doc in cursor2:
            notifications.append(serialize_mongo_doc(doc))

    return success_response(data=notifications, message="Notifications retrieved successfully.")


@router.patch("/{notification_id}/read", summary="Mark single notification as read")
async def mark_as_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    from bson import ObjectId
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(notification_id)
    except Exception:
        return error_response(message="Invalid notification ID format.", status_code=status.HTTP_400_BAD_REQUEST)

    result = await db.get_collection("notifications").update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": {"is_read": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        return error_response(message="Notification not found.", status_code=status.HTTP_404_NOT_FOUND)

    return success_response(message="Notification marked as read.")


@router.patch("/read-all", summary="Mark all notifications as read")
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await db.get_collection("notifications").update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return success_response(message="All notifications marked as read.")

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.database import get_database
from app.core.responses import success_response, error_response
from app.utils.helpers import format_mongo_doc, format_mongo_docs

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


class NotificationItem(BaseModel):
    id: str
    title: str
    message: str
    type: str  # 'booking', 'promo', 'system', 'reminder'
    is_read: bool = False
    created_at: str


@router.get("/unread-count", summary="Get unread notifications count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user.get("id") or current_user.get("_id"))
    user_role = str(current_user.get("role", "customer")).lower()
    is_provider = user_role in ["provider", "service_provider"]
    database = get_database()

    if is_provider:
        query = {
            "$or": [
                {"user_id": user_id},
                {"recipient_role": {"$in": ["provider", "service_provider"]}}
            ],
            "is_read": False
        }
    else:
        query = {"user_id": user_id, "is_read": False}

    count = await database.get_collection("notifications").count_documents(query)
    return success_response(
        data={"unread_count": count},
        message="Unread count retrieved."
    )


@router.get("", summary="Get all notifications for authenticated user")
async def get_user_notifications(current_user: dict = Depends(get_current_user)):
    from bson import ObjectId
    user_id = str(current_user.get("id") or current_user.get("_id"))
    user_role = str(current_user.get("role", "customer")).lower()
    is_provider = user_role in ["provider", "service_provider"]
    database = get_database()

    if is_provider:
        # 1. Purge old promo mock notifications and self-notifications for provider
        await database.get_collection("notifications").delete_many({
            "$or": [{"user_id": user_id}, {"recipient_role": {"$in": ["provider", "service_provider"]}}],
            "title": {"$in": [
                "Welcome to Service Booking! 🎉", "20% Discount Available 🔥", "AI Assistant Ready 🤖",
                "Appointment Confirmed", "Appointment Confirmed ✅", "Appointment Completed", "Appointment Declined"
            ]}
        })

        # 2. Sync all actual appointments into provider notifications
        apt_cursor = database.get_collection("appointments").find().sort("created_at", -1)
        async for apt in apt_cursor:
            apt_id_str = str(apt["_id"])
            status_val = apt.get("status", "Pending")
            client_name = apt.get("user_name", "Client")
            service_title = apt.get("service_name", "Service")
            service_img = apt.get("service_image", "")
            d_str = apt.get("date", "")
            t_str = apt.get("time_slot", "")

            # Look up client profile picture
            client_avatar = apt.get("client_avatar")
            if not client_avatar:
                client_id = apt.get("user_id")
                try:
                    c_user = await database.get_collection("users").find_one({"_id": ObjectId(client_id)})
                except Exception:
                    c_user = await database.get_collection("users").find_one({"id": client_id})
                if not c_user and client_name:
                    c_user = await database.get_collection("users").find_one({"name": client_name})
                if c_user and c_user.get("avatar_url"):
                    client_avatar = c_user["avatar_url"]

            existing = await database.get_collection("notifications").find_one({
                "appointment_id": apt_id_str,
                "recipient_role": {"$in": ["provider", "service_provider"]}
            })

            title = "New Appointment Booking"
            msg = f"{client_name} booked {service_title} on {d_str} at {t_str}."
            if status_val == "Cancelled":
                title = "Appointment Cancelled by Client"
                msg = f"{client_name} has cancelled their appointment for {service_title} on {d_str} at {t_str}."

            if not existing:
                await database.get_collection("notifications").insert_one({
                    "user_id": user_id,
                    "recipient_role": "service_provider",
                    "title": title,
                    "message": msg,
                    "type": "booking",
                    "appointment_id": apt_id_str,
                    "service_id": str(apt.get("service_id", "")),
                    "service_name": service_title,
                    "service_image": service_img,
                    "service_price": float(apt.get("service_price", 0)),
                    "client_name": client_name,
                    "client_avatar": client_avatar or "",
                    "date": d_str,
                    "time_slot": t_str,
                    "status": status_val,
                    "is_read": False,
                    "created_at": apt.get("created_at", datetime.now(timezone.utc).isoformat()),
                })
            else:
                update_doc = {
                    "status": status_val,
                    "service_name": service_title,
                    "service_image": service_img,
                    "client_name": client_name,
                }
                if client_avatar:
                    update_doc["client_avatar"] = client_avatar
                if status_val == "Cancelled":
                    update_doc["title"] = "Appointment Cancelled by Client"
                    update_doc["message"] = f"{client_name} has cancelled their appointment for {service_title} on {d_str} at {t_str}."
                elif existing.get("title") in ["Appointment Confirmed", "Appointment Confirmed ✅", "Appointment Completed", "Appointment Declined"]:
                    update_doc["title"] = "New Appointment Booking"
                    update_doc["message"] = f"{client_name} booked {service_title} on {d_str} at {t_str}."
                await database.get_collection("notifications").update_one(
                    {"_id": existing["_id"]},
                    {"$set": update_doc}
                )

        query = {
            "$or": [
                {"user_id": user_id},
                {"recipient_role": {"$in": ["provider", "service_provider"]}}
            ]
        }
    else:
        query = {"user_id": user_id}

    cursor = database.get_collection("notifications").find(query).sort("created_at", -1)
    notifications = []
    async for doc in cursor:
        notifications.append(format_mongo_doc(doc))

    # If no notifications exist yet for customer, seed initial customer welcome
    if not notifications and user_role != "service_provider":
        default_items = [
            {
                "user_id": user_id,
                "recipient_role": "normal_user",
                "title": "Welcome to Service Booking! 🎉",
                "message": "Explore premium home cleaning, repairs, salon, and plumbing services at your fingertips.",
                "type": "system",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "user_id": user_id,
                "recipient_role": "normal_user",
                "title": "20% Discount Available 🔥",
                "message": "Book your first Deep Cleaning or AC Service today and get up to 20% instant discount.",
                "type": "promo",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "user_id": user_id,
                "recipient_role": "normal_user",
                "title": "AI Assistant Ready 🤖",
                "message": "Need help choosing the right service? Chat with our Gemini AI Service Assistant anytime!",
                "type": "reminder",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        await database.get_collection("notifications").insert_many(default_items)
        cursor2 = database.get_collection("notifications").find(query).sort("created_at", -1)
        async for doc in cursor2:
            notifications.append(format_mongo_doc(doc))

    return success_response(data=notifications, message="Notifications retrieved successfully.")


@router.patch("/{notification_id}/read", summary="Mark single notification as read")
async def mark_as_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    from bson import ObjectId
    user_id = str(current_user.get("id") or current_user.get("_id"))
    user_role = str(current_user.get("role", "customer")).lower()
    database = get_database()
    try:
        oid = ObjectId(notification_id)
    except Exception:
        return error_response(message="Invalid notification ID format.", status_code=status.HTTP_400_BAD_REQUEST)

    match_query = {"_id": oid}
    if user_role == "service_provider":
        match_query["$or"] = [{"user_id": user_id}, {"recipient_role": "service_provider"}]
    else:
        match_query["user_id"] = user_id

    result = await database.get_collection("notifications").update_one(
        match_query,
        {"$set": {"is_read": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        return error_response(message="Notification not found.", status_code=status.HTTP_404_NOT_FOUND)

    return success_response(message="Notification marked as read.")


@router.patch("/read-all", summary="Mark all notifications as read")
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user.get("id") or current_user.get("_id"))
    user_role = str(current_user.get("role", "customer")).lower()
    database = get_database()

    match_query = {"is_read": False}
    if user_role == "service_provider":
        match_query["$or"] = [{"user_id": user_id}, {"recipient_role": "service_provider"}]
    else:
        match_query["user_id"] = user_id

    await database.get_collection("notifications").update_many(
        match_query,
        {"$set": {"is_read": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return success_response(message="All notifications marked as read.")


@router.delete("/{notification_id}", summary="Delete single notification")
async def delete_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    from bson import ObjectId
    user_id = str(current_user.get("id") or current_user.get("_id"))
    user_role = str(current_user.get("role", "customer")).lower()
    database = get_database()
    try:
        oid = ObjectId(notification_id)
    except Exception:
        return error_response(message="Invalid notification ID format.", status_code=status.HTTP_400_BAD_REQUEST)

    match_query = {"_id": oid}
    if user_role == "service_provider":
        match_query["$or"] = [{"user_id": user_id}, {"recipient_role": "service_provider"}]
    else:
        match_query["user_id"] = user_id

    result = await database.get_collection("notifications").delete_one(match_query)
    if result.deleted_count == 0:
        return error_response(message="Notification not found.", status_code=status.HTTP_404_NOT_FOUND)

    return success_response(message="Notification deleted successfully.")


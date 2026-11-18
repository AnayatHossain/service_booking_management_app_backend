from datetime import datetime, timezone
from bson import ObjectId
from typing import List, Optional
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.appointments.schemas import CreateAppointmentRequest, AppointmentStatus
from app.utils.helpers import format_mongo_doc, format_mongo_docs


async def check_slot_availability(
    db: AsyncIOMotorDatabase,
    service_id: str,
    date: str,
    time_slot: str
) -> bool:
    """Returns True if the time slot is free, False if already booked."""
    conflict = await db.appointments.find_one({
        "service_id": service_id,
        "date": date,
        "time_slot": time_slot,
        "status": {"$ne": AppointmentStatus.CANCELLED.value}
    })
    return conflict is None


async def get_service_slot_availability(
    db: AsyncIOMotorDatabase,
    service_id: str,
    date: str
) -> dict:
    """Returns a list of all slots with their availability status for a given service and date."""
    try:
        oid = ObjectId(service_id)
        service = await db.services.find_one({"_id": oid})
    except Exception:
        service = await db.services.find_one({"id": service_id})

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")

    all_slots = service.get("time_slots", [
        "09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM",
        "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
    ])

    # Find booked slots on this date
    booked_cursor = db.appointments.find({
        "service_id": service_id,
        "date": date,
        "status": {"$ne": AppointmentStatus.CANCELLED.value}
    }, {"time_slot": 1})

    booked_docs = await booked_cursor.to_list(length=100)
    booked_slots = {b["time_slot"] for b in booked_docs}

    slot_status_list = [
        {"slot": slot, "is_available": (slot not in booked_slots)}
        for slot in all_slots
    ]

    return {
        "service_id": service_id,
        "date": date,
        "slots": slot_status_list
    }


async def create_appointment(
    db: AsyncIOMotorDatabase,
    user: dict,
    req: CreateAppointmentRequest
) -> dict:
    # 1. Fetch target service
    booking_date = req.date or req.appointment_date
    if not booking_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Appointment date is required (date or appointment_date)."
        )

    try:
        oid = ObjectId(req.service_id)
        service = await db.services.find_one({"_id": oid})
    except Exception:
        service = await db.services.find_one({"id": req.service_id})

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested service does not exist."
        )

    # 2. Check slot conflict
    is_free = await check_slot_availability(db, req.service_id, booking_date, req.time_slot)
    if not is_free:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is already booked. Please choose an available time slot."
        )

    # 3. Create appointment record
    now = datetime.now(timezone.utc).isoformat()
    appointment_doc = {
        "user_id": str(user["id"]),
        "user_name": user.get("name", "Customer"),
        "user_email": user.get("email"),
        "service_id": req.service_id,
        "service_name": service.get("name"),
        "service_category": service.get("category"),
        "service_price": float(service.get("price", 0)),
        "service_image": service.get("image_url", ""),
        "provider_id": service.get("provider_id"),
        "provider_name": service.get("provider_name", "Verified Service Provider"),
        "duration_minutes": int(service.get("duration_minutes", 60)),
        "date": booking_date,
        "time_slot": req.time_slot,
        "customer_notes": req.customer_notes.strip() if req.customer_notes else None,
        "status": AppointmentStatus.PENDING.value,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.appointments.insert_one(appointment_doc)
    appointment_doc["_id"] = result.inserted_id
    apt_id_str = str(result.inserted_id)

    # 1. Real notification for User
    service_title = service.get("name", "Service")
    service_img = service.get("image_url", "")
    service_price_val = float(service.get("price", 0))
    client_name_val = user.get("name", "Client")
    client_avatar_val = user.get("avatar_url", "")

    await db.notifications.insert_one({
        "user_id": str(user["id"]),
        "recipient_role": "normal_user",
        "title": "Booking Submitted",
        "message": f"Congratulations! Your booking for {service_title} on {booking_date} at {req.time_slot} is now pending.",
        "type": "booking",
        "appointment_id": apt_id_str,
        "service_id": str(service.get("_id") or service.get("id")),
        "service_name": service_title,
        "service_image": service_img,
        "service_price": service_price_val,
        "client_name": client_name_val,
        "client_avatar": client_avatar_val,
        "date": booking_date,
        "time_slot": req.time_slot,
        "status": "Pending",
        "is_read": False,
        "created_at": now,
    })

    # 2. Real notification for Service Provider
    provider_id_val = str(service.get("provider_id")) if service.get("provider_id") else None
    await db.notifications.insert_one({
        "user_id": provider_id_val,
        "recipient_role": "service_provider",
        "title": "New Appointment Booking",
        "message": f"{client_name_val} has booked an appointment for {service_title} on {booking_date} at {req.time_slot}.",
        "type": "booking",
        "appointment_id": apt_id_str,
        "service_id": str(service.get("_id") or service.get("id")),
        "service_name": service_title,
        "service_image": service_img,
        "service_price": service_price_val,
        "client_name": client_name_val,
        "client_avatar": client_avatar_val,
        "date": booking_date,
        "time_slot": req.time_slot,
        "status": "Pending",
        "is_read": False,
        "created_at": now,
    })

    return format_mongo_doc(appointment_doc)


async def list_user_appointments(
    db: AsyncIOMotorDatabase,
    user_id: str,
    status_filter: Optional[str] = None
) -> List[dict]:
    query: dict = {"user_id": str(user_id)}
    if status_filter and status_filter.strip().lower() != "all":
        query["status"] = {"$regex": f"^{status_filter.strip()}$", "$options": "i"}

    cursor = db.appointments.find(query).sort([("date", -1), ("time_slot", -1)])
    appointments = await cursor.to_list(length=100)
    for apt in appointments:
        if not apt.get("service_image"):
            try:
                s_oid = ObjectId(apt.get("service_id"))
                s = await db.services.find_one({"_id": s_oid})
            except Exception:
                s = await db.services.find_one({"id": apt.get("service_id")})
            if s and s.get("image_url"):
                apt["service_image"] = s["image_url"]
    return format_mongo_docs(appointments)


async def get_appointment_by_id(
    db: AsyncIOMotorDatabase,
    appointment_id: str,
    user_id: str
) -> dict:
    apt = None
    try:
        oid = ObjectId(appointment_id)
        apt = await db.appointments.find_one({"_id": oid, "$or": [{"user_id": str(user_id)}, {"provider_id": str(user_id)}]})
    except Exception:
        apt = await db.appointments.find_one({"id": appointment_id, "$or": [{"user_id": str(user_id)}, {"provider_id": str(user_id)}]})

    if not apt:
        try:
            apt = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
        except Exception:
            apt = await db.appointments.find_one({"id": appointment_id})

    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or you are not authorized to view it."
        )

    # Enrich client avatar if not present
    if not apt.get("user_avatar"):
        try:
            u_oid = ObjectId(apt.get("user_id"))
            u = await db.users.find_one({"_id": u_oid})
        except Exception:
            u = await db.users.find_one({"id": apt.get("user_id")})
        if not u and apt.get("user_name"):
            u = await db.users.find_one({"name": apt.get("user_name")})
        if u and u.get("avatar_url"):
            apt["user_avatar"] = u["avatar_url"]

    return format_mongo_doc(apt)


async def cancel_user_appointment(
    db: AsyncIOMotorDatabase,
    appointment_id: str,
    user_id: str
) -> dict:
    try:
        oid = ObjectId(appointment_id)
        apt = await db.appointments.find_one({"_id": oid, "user_id": str(user_id)})
    except Exception:
        oid = appointment_id
        apt = await db.appointments.find_one({"id": appointment_id, "user_id": str(user_id)})

    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or not owned by you."
        )

    if apt.get("status") == AppointmentStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This appointment has already been cancelled."
        )

    if apt.get("status") == AppointmentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel an appointment that is already completed."
        )

    now = datetime.now(timezone.utc).isoformat()
    updated = await db.appointments.find_one_and_update(
        {"_id": apt["_id"]},
        {"$set": {"status": AppointmentStatus.CANCELLED.value, "updated_at": now}},
        return_document=True
    )

    # 1. Update any existing notification status
    apt_id_str = str(apt["_id"])
    await db.notifications.update_many(
        {"appointment_id": apt_id_str},
        {"$set": {"status": "Cancelled", "updated_at": now}}
    )

    # 2. Customer Notification
    service_title = apt.get("service_name") or "Service"
    service_img = apt.get("service_image", "")
    service_price_val = float(apt.get("service_price", 0))
    client_name_val = apt.get("user_name", "Client")
    date_val = apt.get("date", "")
    time_slot_val = apt.get("time_slot", "")

    await db.notifications.insert_one({
        "user_id": str(user_id),
        "recipient_role": "normal_user",
        "title": "Booking Cancelled",
        "message": f"Your appointment for {service_title} on {date_val} at {time_slot_val} has been cancelled.",
        "type": "booking",
        "appointment_id": apt_id_str,
        "service_id": str(apt.get("service_id", "")),
        "service_name": service_title,
        "service_image": service_img,
        "service_price": service_price_val,
        "client_name": client_name_val,
        "date": date_val,
        "time_slot": time_slot_val,
        "status": "Cancelled",
        "is_read": False,
        "created_at": now,
    })

    # 3. Provider Notification
    provider_id_val = str(apt.get("provider_id")) if apt.get("provider_id") else None
    await db.notifications.insert_one({
        "user_id": provider_id_val,
        "recipient_role": "service_provider",
        "title": "Appointment Cancelled by Client",
        "message": f"{client_name_val} has cancelled their appointment for {service_title} on {date_val} at {time_slot_val}.",
        "type": "booking",
        "appointment_id": apt_id_str,
        "service_id": str(apt.get("service_id", "")),
        "service_name": service_title,
        "service_image": service_img,
        "service_price": service_price_val,
        "client_name": client_name_val,
        "date": date_val,
        "time_slot": time_slot_val,
        "status": "Cancelled",
        "is_read": False,
        "created_at": now,
    })

    return format_mongo_doc(updated)


async def list_provider_appointments(db: AsyncIOMotorDatabase, provider_id: str, status_filter: Optional[str] = None) -> List[dict]:
    query: dict = {}
    if status_filter and status_filter.strip() and status_filter.strip().lower() != "all":
        query["status"] = {"$regex": f"^{status_filter.strip()}$", "$options": "i"}

    cursor = db.appointments.find(query).sort("created_at", -1)
    appointments = await cursor.to_list(length=200)
    for apt in appointments:
        if not apt.get("service_image"):
            try:
                s_oid = ObjectId(apt.get("service_id"))
                s = await db.services.find_one({"_id": s_oid})
            except Exception:
                s = await db.services.find_one({"id": apt.get("service_id")})
            if s and s.get("image_url"):
                apt["service_image"] = s["image_url"]
    return format_mongo_docs(appointments)


async def update_appointment_status_by_provider(db: AsyncIOMotorDatabase, appointment_id: str, new_status: str) -> dict:
    valid_statuses = ["Pending", "Confirmed", "Completed", "Cancelled"]
    matched_status = next((s for s in valid_statuses if s.lower() == new_status.strip().lower()), None)
    if not matched_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{new_status}'. Allowed: {', '.join(valid_statuses)}"
        )

    try:
        oid = ObjectId(appointment_id)
        apt = await db.appointments.find_one({"_id": oid})
    except Exception:
        apt = await db.appointments.find_one({"id": appointment_id})

    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found."
        )

    now = datetime.now(timezone.utc).isoformat()
    updated = await db.appointments.find_one_and_update(
        {"_id": apt["_id"]},
        {"$set": {"status": matched_status, "updated_at": now}},
        return_document=True
    )

    apt_id_str = str(apt["_id"])
    customer_id = apt.get("user_id")
    service_title = apt.get("service_name") or "Service"
    service_img = apt.get("service_image", "")
    service_price_val = float(apt.get("service_price", 0))
    client_name_val = apt.get("user_name", "Client")
    date_str = apt.get("date", "")
    time_str = apt.get("time_slot", "")
    provider_id_val = str(apt.get("provider_id")) if apt.get("provider_id") else None

    # Update any existing notification associated with this appointment
    await db.notifications.update_many(
        {"appointment_id": apt_id_str},
        {"$set": {"status": matched_status, "updated_at": now}}
    )

    if customer_id:
        if matched_status == "Confirmed":
            # Notification for Customer
            await db.notifications.insert_one({
                "user_id": customer_id,
                "recipient_role": "normal_user",
                "title": "Booking Confirmed",
                "message": f"Great news! Your booking for {service_title} on {date_str} at {time_str} has been confirmed.",
                "type": "booking",
                "appointment_id": apt_id_str,
                "service_id": str(apt.get("service_id", "")),
                "service_name": service_title,
                "service_image": service_img,
                "service_price": service_price_val,
                "client_name": client_name_val,
                "date": date_str,
                "time_slot": time_str,
                "status": "Confirmed",
                "is_read": False,
                "created_at": now,
            })
        elif matched_status == "Completed":
            # Notification for Customer (with prompt to rate)
            await db.notifications.insert_one({
                "user_id": customer_id,
                "recipient_role": "normal_user",
                "title": "Service Completed",
                "message": f"Your appointment for {service_title} on {date_str} was completed. Tap here to rate and review your experience!",
                "type": "booking",
                "appointment_id": apt_id_str,
                "service_id": str(apt.get("service_id", "")),
                "service_name": service_title,
                "service_image": service_img,
                "service_price": service_price_val,
                "client_name": client_name_val,
                "date": date_str,
                "time_slot": time_str,
                "status": "Completed",
                "can_review": True,
                "is_read": False,
                "created_at": now,
            })
        elif matched_status == "Cancelled":
            # Notification for Customer
            await db.notifications.insert_one({
                "user_id": customer_id,
                "recipient_role": "normal_user",
                "title": "Booking Declined",
                "message": f"Your appointment for {service_title} on {date_str} at {time_str} was declined by the provider.",
                "type": "booking",
                "appointment_id": apt_id_str,
                "service_id": str(apt.get("service_id", "")),
                "service_name": service_title,
                "service_image": service_img,
                "service_price": service_price_val,
                "client_name": client_name_val,
                "date": date_str,
                "time_slot": time_str,
                "status": "Cancelled",
                "is_read": False,
                "created_at": now,
            })

    return format_mongo_doc(updated)


async def rate_appointment(db: AsyncIOMotorDatabase, appointment_id: str, user_id: str, rating_val: float, review_text: Optional[str] = None) -> dict:
    try:
        oid = ObjectId(appointment_id)
        apt = await db.appointments.find_one({"_id": oid, "user_id": str(user_id)})
    except Exception:
        apt = await db.appointments.find_one({"id": appointment_id, "user_id": str(user_id)})

    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or not owned by you."
        )

    if apt.get("status") != AppointmentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed appointments can be rated."
        )

    # If already rated, route to update_appointment_rating
    if apt.get("is_rated") is True:
        return await update_appointment_rating(db, appointment_id, user_id, rating_val, review_text)

    now = datetime.now(timezone.utc).isoformat()
    # Update appointment with rating
    updated_apt = await db.appointments.find_one_and_update(
        {"_id": apt["_id"]},
        {"$set": {
            "is_rated": True,
            "rating": rating_val,
            "review": review_text.strip() if review_text else None,
            "rated_at": now,
            "updated_at": now
        }},
        return_document=True
    )

    # Recalculate service rating in MongoDB
    service = None
    service_id = apt.get("service_id")
    if service_id:
        try:
            s_oid = ObjectId(service_id)
            service = await db.services.find_one({"_id": s_oid})
        except Exception:
            service = await db.services.find_one({"id": service_id})

    # Fallback to service_name if not found by id
    if not service and apt.get("service_name"):
        service = await db.services.find_one({"name": apt.get("service_name")})

    if service:
        old_reviews = int(service.get("total_reviews", 0))
        old_rating = float(service.get("rating", 4.8))
        new_reviews = old_reviews + 1
        new_rating = round(((old_rating * old_reviews) + rating_val) / new_reviews, 2)

        await db.services.update_one(
            {"_id": service["_id"]},
            {"$set": {
                "total_reviews": new_reviews,
                "rating": new_rating,
                "updated_at": now
            }}
        )

    # Mark all existing notifications for this appointment as rated
    await db.notifications.update_many(
        {"appointment_id": str(apt["_id"])},
        {"$set": {
            "is_rated": True,
            "rating": rating_val,
            "review": review_text.strip() if review_text else None,
            "updated_at": now
        }}
    )

    # Insert Rating Notification for Provider
    provider_id_val = str(apt.get("provider_id")) if apt.get("provider_id") else None
    if not provider_id_val and service:
        provider_id_val = str(service.get("provider_id")) if service.get("provider_id") else None

    client_name_val = apt.get("user_name", "A client")
    service_title = apt.get("service_name") or (service.get("name") if service else "Service")
    review_snippet = f': "{review_text.strip()}"' if review_text and review_text.strip() else ""

    await db.notifications.insert_one({
        "user_id": provider_id_val,
        "recipient_role": "service_provider",
        "title": "New Client Rating",
        "message": f"{client_name_val} gave {rating_val:.1f}★ rating for {service_title}{review_snippet}",
        "type": "review",
        "appointment_id": str(apt["_id"]),
        "service_id": str(service["_id"]) if service and "_id" in service else (str(service_id) if service_id else ""),
        "service_name": service_title,
        "service_image": apt.get("service_image", "") or (service.get("image_url", "") if service else ""),
        "client_name": client_name_val,
        "rating": rating_val,
        "review": review_text.strip() if review_text else None,
        "status": "Completed",
        "is_read": False,
        "created_at": now,
    })

    return format_mongo_doc(updated_apt)


async def update_appointment_rating(
    db: AsyncIOMotorDatabase,
    appointment_id: str,
    user_id: str,
    rating_val: float,
    review_text: Optional[str] = None
) -> dict:
    try:
        oid = ObjectId(appointment_id)
        apt = await db.appointments.find_one({"_id": oid, "user_id": str(user_id)})
    except Exception:
        apt = await db.appointments.find_one({"id": appointment_id, "user_id": str(user_id)})

    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or not owned by you."
        )

    now = datetime.now(timezone.utc).isoformat()
    old_rating = float(apt.get("rating", rating_val) or rating_val)

    updated_apt = await db.appointments.find_one_and_update(
        {"_id": apt["_id"]},
        {"$set": {
            "is_rated": True,
            "rating": rating_val,
            "review": review_text.strip() if review_text else None,
            "updated_at": now
        }},
        return_document=True
    )

    # Recalculate service rating
    service = None
    service_id = apt.get("service_id")
    if service_id:
        try:
            s_oid = ObjectId(service_id)
            service = await db.services.find_one({"_id": s_oid})
        except Exception:
            service = await db.services.find_one({"id": service_id})

    if not service and apt.get("service_name"):
        service = await db.services.find_one({"name": apt.get("service_name")})

    if service:
        tot_rev = max(1, int(service.get("total_reviews", 1)))
        current_serv_rating = float(service.get("rating", 4.8))
        diff = rating_val - old_rating
        new_serv_rating = round(max(1.0, min(5.0, current_serv_rating + (diff / tot_rev))), 2)

        await db.services.update_one(
            {"_id": service["_id"]},
            {"$set": {
                "rating": new_serv_rating,
                "updated_at": now
            }}
        )

    client_name_val = apt.get("user_name", "A client")
    service_title = apt.get("service_name") or (service.get("name") if service else "Service")
    review_snippet = f': "{review_text.strip()}"' if review_text and review_text.strip() else ""

    # Update any review notification
    await db.notifications.update_many(
        {"appointment_id": str(apt["_id"]), "type": "review"},
        {"$set": {
            "rating": rating_val,
            "review": review_text.strip() if review_text else None,
            "message": f"{client_name_val} gave {rating_val:.1f}★ rating for {service_title}{review_snippet}",
            "updated_at": now
        }}
    )

    # Update general booking notifications
    await db.notifications.update_many(
        {"appointment_id": str(apt["_id"])},
        {"$set": {
            "is_rated": True,
            "rating": rating_val,
            "review": review_text.strip() if review_text else None,
            "updated_at": now
        }}
    )

    return format_mongo_doc(updated_apt)


async def delete_appointment_rating(
    db: AsyncIOMotorDatabase,
    appointment_id: str,
    user_id: str
) -> dict:
    try:
        oid = ObjectId(appointment_id)
        apt = await db.appointments.find_one({"_id": oid, "user_id": str(user_id)})
    except Exception:
        apt = await db.appointments.find_one({"id": appointment_id, "user_id": str(user_id)})

    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or not owned by you."
        )

    now = datetime.now(timezone.utc).isoformat()
    old_rating = float(apt.get("rating", 5.0) or 5.0)

    # Clear rating fields from appointment
    updated_apt = await db.appointments.find_one_and_update(
        {"_id": apt["_id"]},
        {
            "$set": {
                "is_rated": False,
                "rating": None,
                "review": None,
                "updated_at": now
            },
            "$unset": {
                "rated_at": ""
            }
        },
        return_document=True
    )

    # Adjust service rating
    service = None
    service_id = apt.get("service_id")
    if service_id:
        try:
            s_oid = ObjectId(service_id)
            service = await db.services.find_one({"_id": s_oid})
        except Exception:
            service = await db.services.find_one({"id": service_id})

    if not service and apt.get("service_name"):
        service = await db.services.find_one({"name": apt.get("service_name")})

    if service:
        cur_reviews = int(service.get("total_reviews", 1))
        new_reviews = max(0, cur_reviews - 1)
        cur_rating = float(service.get("rating", 4.8))

        if new_reviews > 0:
            new_rating = round(max(1.0, min(5.0, ((cur_rating * cur_reviews) - old_rating) / new_reviews)), 2)
        else:
            new_rating = 4.8

        await db.services.update_one(
            {"_id": service["_id"]},
            {"$set": {
                "total_reviews": new_reviews,
                "rating": new_rating,
                "updated_at": now
            }}
        )

    # Delete any review notification sent to provider
    await db.notifications.delete_many(
        {"appointment_id": str(apt["_id"]), "type": "review"}
    )

    # Reset rating fields in existing booking notifications so customer can rate again
    await db.notifications.update_many(
        {"appointment_id": str(apt["_id"])},
        {
            "$set": {
                "is_rated": False,
                "can_review": True,
                "updated_at": now
            },
            "$unset": {
                "rating": "",
                "review": ""
            }
        }
    )

    return format_mongo_doc(updated_apt)

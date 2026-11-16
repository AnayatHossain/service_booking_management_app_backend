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
    is_free = await check_slot_availability(db, req.service_id, req.date, req.time_slot)
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
        "duration_minutes": int(service.get("duration_minutes", 60)),
        "date": req.date,
        "time_slot": req.time_slot,
        "customer_notes": req.customer_notes.strip() if req.customer_notes else None,
        "status": AppointmentStatus.CONFIRMED.value,  # Auto-confirm on successful booking
        "created_at": now,
        "updated_at": now,
    }

    result = await db.appointments.insert_one(appointment_doc)
    appointment_doc["_id"] = result.inserted_id
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
    return format_mongo_docs(appointments)


async def get_appointment_by_id(
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
            detail="Appointment not found or you are not authorized to view it."
        )

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

    return format_mongo_doc(updated)

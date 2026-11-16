from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.deps import get_current_user
from app.core.responses import success_response
from app.modules.appointments.schemas import CreateAppointmentRequest
from app.modules.appointments.service import (
    create_appointment,
    get_service_slot_availability,
    list_user_appointments,
    get_appointment_by_id,
    cancel_user_appointment,
)

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@router.post("", summary="Book a new appointment")
async def book_appointment(
    req: CreateAppointmentRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    appointment = await create_appointment(db, current_user, req)
    return success_response(
        data=appointment,
        message="Appointment booked successfully!",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/availability", summary="Check time slot availability for a service on a given date")
async def check_availability(
    service_id: str = Query(..., description="Service ID"),
    date: str = Query(..., description="Date (YYYY-MM-DD)"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    availability = await get_service_slot_availability(db, service_id, date)
    return success_response(
        data=availability,
        message="Availability retrieved successfully."
    )


@router.get("/my", summary="Retrieve all appointments belonging to the authenticated customer")
async def get_my_appointments(
    status: Optional[str] = Query(None, description="Optional status filter: Pending, Confirmed, Cancelled, Completed"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    appointments = await list_user_appointments(db, current_user["id"], status_filter=status)
    return success_response(
        data=appointments,
        message="Appointments retrieved successfully.",
        meta={"total": len(appointments)}
    )


@router.get("/{appointment_id}", summary="Get individual appointment details")
async def get_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    apt = await get_appointment_by_id(db, appointment_id, current_user["id"])
    return success_response(
        data=apt,
        message="Appointment details retrieved."
    )


@router.patch("/{appointment_id}/cancel", summary="Cancel a scheduled appointment")
async def cancel_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    updated = await cancel_user_appointment(db, appointment_id, current_user["id"])
    return success_response(
        data=updated,
        message="Appointment cancelled successfully."
    )

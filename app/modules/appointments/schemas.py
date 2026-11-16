from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AppointmentStatus(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"


class CreateAppointmentRequest(BaseModel):
    service_id: str = Field(..., description="Target service ID")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Appointment date in YYYY-MM-DD format")
    time_slot: str = Field(..., description="Selected time slot, e.g. '10:00 AM'")
    customer_notes: Optional[str] = Field(None, max_length=500, description="Optional booking notes")


class CheckSlotRequest(BaseModel):
    service_id: str
    date: str
    time_slot: str


class AppointmentResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    service_id: str
    service_name: str
    service_category: str
    service_price: float
    service_image: str
    date: str
    time_slot: str
    duration_minutes: int
    status: AppointmentStatus
    customer_notes: Optional[str] = None
    created_at: str
    updated_at: str

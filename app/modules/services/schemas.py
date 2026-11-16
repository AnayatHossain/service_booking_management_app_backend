from pydantic import BaseModel, Field
from typing import Optional, List


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(...)
    category: str = Field(...)
    price: float = Field(..., gt=0)
    duration_minutes: int = Field(..., gt=0)
    image_url: str = Field(...)
    is_featured: bool = False
    rating: float = Field(4.8, ge=0, le=5.0)
    total_reviews: int = Field(0, ge=0)
    available_days: List[str] = Field(default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
    time_slots: List[str] = Field(default=[
        "09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM",
        "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
    ])


class ServiceResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    price: float
    duration_minutes: int
    image_url: str
    is_featured: bool
    rating: float
    total_reviews: int
    available_days: List[str]
    time_slots: List[str]

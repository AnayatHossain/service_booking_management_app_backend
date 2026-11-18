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
    includes: Optional[List[str]] = Field(default=[
        "Vetted & background checked professionals",
        "Comprehensive servicing with quality check",
        "Full satisfaction guarantee with free rework",
        "24/7 dedicated in-app support & easy cancel"
    ])
    available_days: List[str] = Field(default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
    time_slots: List[str] = Field(default=[
        "09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM",
        "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
    ])


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    duration_minutes: Optional[int] = None
    image_url: Optional[str] = None
    is_featured: Optional[bool] = None
    rating: Optional[float] = None
    total_reviews: Optional[int] = None
    includes: Optional[List[str]] = None
    available_days: Optional[List[str]] = None
    time_slots: Optional[List[str]] = None


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
    includes: Optional[List[str]] = None
    available_days: List[str]
    time_slots: List[str]

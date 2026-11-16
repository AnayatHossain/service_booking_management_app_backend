from pydantic import BaseModel, Field
from typing import Optional


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=60)
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current account password")
    new_password: str = Field(..., min_length=6, description="New password")

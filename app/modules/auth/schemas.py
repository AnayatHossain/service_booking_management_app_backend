from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=60, description="Full name")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, description="Password (at least 6 characters)")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserProfile(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "customer"
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None


class AuthData(BaseModel):
    user: UserProfile
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int

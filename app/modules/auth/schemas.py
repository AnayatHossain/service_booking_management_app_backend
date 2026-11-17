from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=60, description="Full name")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, description="Password (at least 6 characters)")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    role: Optional[str] = Field("customer", description="User role: customer or provider")
    institution_name: Optional[str] = Field(None, max_length=100, description="Business or institution name for providers")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserProfile(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "customer"
    institution_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None


class AuthData(BaseModel):
    user: UserProfile
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int

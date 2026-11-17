from datetime import datetime, timezone
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import hash_password, check_password, create_access_token
from app.core.config import settings
from app.modules.auth.schemas import RegisterRequest, LoginRequest
from app.utils.helpers import format_mongo_doc


async def register_user(db: AsyncIOMotorDatabase, req: RegisterRequest) -> dict:
    email_clean = req.email.strip().lower()

    existing = await db.users.find_one({"email": email_clean})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    now = datetime.now(timezone.utc).isoformat()
    role = "provider" if req.role in ["provider", "service_provider"] else "customer"
    new_user = {
        "name": req.name.strip(),
        "email": email_clean,
        "password": hash_password(req.password),
        "phone": req.phone.strip() if req.phone else None,
        "role": role,
        "institution_name": req.institution_name.strip() if req.institution_name else None,
        "avatar_url": f"https://api.dicebear.com/7.x/initials/svg?seed={req.name.strip()}",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.users.insert_one(new_user)
    new_user["_id"] = result.inserted_id
    user_formatted = format_mongo_doc(new_user)
    user_formatted.pop("password", None)

    token = create_access_token(user_formatted)

    return {
        "user": user_formatted,
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": settings.jwt_expire_minutes,
    }


async def login_user(db: AsyncIOMotorDatabase, req: LoginRequest) -> dict:
    email_clean = req.email.strip().lower()

    user = await db.users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not check_password(req.password, user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently disabled."
        )

    user_formatted = format_mongo_doc(user)
    user_formatted.pop("password", None)

    token = create_access_token(user_formatted)

    return {
        "user": user_formatted,
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": settings.jwt_expire_minutes,
    }

from fastapi import APIRouter, Depends, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.deps import get_current_user
from app.core.responses import success_response, error_response
from app.core.brute_force import protector
from app.core.rate_limit import get_client_ip
from app.modules.auth.schemas import RegisterRequest, LoginRequest
from app.modules.auth.service import register_user, login_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", summary="Register a new customer account")
async def register(req: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    auth_data = await register_user(db, req)
    return success_response(
        data=auth_data,
        message="Registration successful. Welcome to Service Booking!",
        status_code=status.HTTP_201_CREATED
    )


@router.post("/login", summary="Sign in with email and password")
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    ip = get_client_ip(request)
    protector.check_lockout(ip, req.email)

    try:
        auth_data = await login_user(db, req)
        protector.record_success(ip, req.email)
        return success_response(
            data=auth_data,
            message="Login successful."
        )
    except Exception as e:
        protector.record_failure(ip, req.email)
        raise e


@router.get("/me", summary="Get authenticated customer profile")
async def get_me(current_user: dict = Depends(get_current_user)):
    return success_response(
        data=current_user,
        message="Profile retrieved successfully."
    )


@router.post("/logout", summary="Logout authenticated session")
async def logout(current_user: dict = Depends(get_current_user)):
    return success_response(
        data=None,
        message="Logged out successfully."
    )

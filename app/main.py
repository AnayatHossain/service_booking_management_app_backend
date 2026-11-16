from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.rate_limit import RateLimiterMiddleware
from app.core.responses import Utf8JSONResponse, success_response, error_response

# Module routers
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.services.router import router as services_router
from app.modules.appointments.router import router as appointments_router
from app.modules.ai_assistant.router import router as ai_router
from app.modules.notifications.router import router as notifications_router


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces OWASP recommended security headers on all API responses and strips server disclosures."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Strip server & framework disclosure headers
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="Service Booking & Management API",
    description="Full-featured RESTful API for Service Booking & Management mobile application with AI integration.",
    version="1.0.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
    default_response_class=Utf8JSONResponse,
    lifespan=lifespan,
)

# 1. Security & Header middleware
app.add_middleware(SecurityHeadersMiddleware)

# 2. Rate limiting middleware (Sliding-window)
app.add_middleware(RateLimiterMiddleware)

# 3. CORS configuration (allowing cross-origin requests from Flutter app, emulators & web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(
        message=str(exc.detail),
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}"
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        formatted_errors.append({
            "field": field,
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error")
        })
    return error_response(
        message="Request validation failed. Please check the supplied fields.",
        status_code=422,
        error_code="VALIDATION_ERROR",
        errors=formatted_errors
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return error_response(
        message="An unexpected internal server error occurred.",
        status_code=500,
        error_code="INTERNAL_SERVER_ERROR",
        errors=str(exc) if settings.environment == "development" else None
    )


# Health check & root endpoints
@app.get("/", tags=["System"])
async def root():
    return success_response(
        data={
            "app": "Service Booking & Management API",
            "version": "1.0.0",
            "docs": "/docs",
            "status": "healthy"
        },
        message="Welcome to Service Booking & Management API"
    )


@app.get("/api/health", tags=["System"])
async def health():
    return success_response(
        data={"status": "operational", "environment": settings.environment},
        message="System healthy."
    )


# Register modular routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(services_router)
app.include_router(appointments_router)
app.include_router(ai_router)
app.include_router(notifications_router)

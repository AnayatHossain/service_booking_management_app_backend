import time
import threading
from collections import deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Extract real client IP from Cloudflare, reverse proxy or direct socket."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


class RateLimiter:
    """Thread-safe, sliding-window in-memory rate limiter with auto-cleanup."""

    def __init__(self):
        self._history: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()
        self._last_clean = time.monotonic()
        self._clean_interval = 60.0  # seconds

    def _get_tier_and_limit(self, path: str) -> tuple[str, int]:
        clean = path.lower()

        # Auth and sensitive routes
        if any(p in clean for p in ("/auth/login", "/auth/register", "/users/change-password")):
            return "auth", settings.rate_limit_auth_per_minute

        # AI Assistant routes (give adequate headroom for conversation while protecting abuse)
        if "/ai/" in clean:
            return "ai", 30

        # General API routes
        return "general", settings.rate_limit_per_minute

    def check_rate_limit(self, ip: str, path: str) -> tuple[bool, int, int, int]:
        """Check whether request is allowed.
        Returns: (allowed, limit, remaining, retry_after)
        """
        now = time.monotonic()
        tier, limit = self._get_tier_and_limit(path)
        key = (ip, tier)
        window = 60.0

        with self._lock:
            if now - self._last_clean > self._clean_interval:
                self._cleanup_locked(now, window)
                self._last_clean = now

            timestamps = self._history.setdefault(key, deque())

            # Remove timestamps outside the sliding window
            cutoff = now - window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            count = len(timestamps)
            if count >= limit:
                oldest = timestamps[0]
                retry_after = max(1, int(oldest + window - now) + 1)
                return False, limit, 0, retry_after

            timestamps.append(now)
            remaining = max(0, limit - len(timestamps))
            return True, limit, remaining, 0

    def _cleanup_locked(self, now: float, window: float) -> None:
        cutoff = now - window
        stale_keys = []
        for key, dq in self._history.items():
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if not dq:
                stale_keys.append(key)
        for key in stale_keys:
            self._history.pop(key, None)


limiter = RateLimiter()


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude documentation / health routes
        if request.url.path in ("/docs", "/redoc", "/openapi.json", "/api/health", "/"):
            return await call_next(request)

        ip = get_client_ip(request)
        allowed, limit, remaining, retry_after = limiter.check_rate_limit(ip, request.url.path)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Too many requests. Please slow down.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after_seconds": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

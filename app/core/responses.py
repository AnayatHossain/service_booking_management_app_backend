from typing import Any, Optional
from fastapi.responses import JSONResponse


class Utf8JSONResponse(JSONResponse):
    """JSON response that explicitly declares charset=utf-8.
    
    Prevents latin1 fallback on HTTP clients (e.g. Flutter/Dart http package),
    ensuring special characters and unicode strings are preserved without mojibake.
    """
    media_type = "application/json; charset=utf-8"


def success_response(
    data: Any = None,
    message: str = "Request successful",
    status_code: int = 200,
    meta: Optional[dict] = None
) -> Utf8JSONResponse:
    content = {
        "success": True,
        "message": message,
        "data": data,
    }
    if meta is not None:
        content["meta"] = meta
    return Utf8JSONResponse(content=content, status_code=status_code)


def error_response(
    message: str = "An error occurred",
    status_code: int = 400,
    error_code: Optional[str] = None,
    errors: Any = None
) -> Utf8JSONResponse:
    content = {
        "success": False,
        "message": message,
        "error_code": error_code or f"ERR_{status_code}",
    }
    if errors is not None:
        content["errors"] = errors
    return Utf8JSONResponse(content=content, status_code=status_code)

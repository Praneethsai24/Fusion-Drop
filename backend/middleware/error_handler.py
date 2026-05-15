# backend/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.core.exceptions import AppException


async def app_exception_handler(request: Request, exc: AppException):
    """
    Convert AppException into a JSON response.

    We keep the top-level `detail` field for compatibility with FastAPI's
    default error shape, but add structured information under the hood.
    """
    payload = {
        "detail": exc.message,
        "code": exc.code,
        "extra": exc.extra,
    }
    return JSONResponse(status_code=400, content=payload)
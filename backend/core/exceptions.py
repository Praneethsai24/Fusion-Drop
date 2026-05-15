"""Centralised exception types and FastAPI exception handlers."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.core.logging import get_logger

logger = get_logger(__name__)


class FusionDropException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(FusionDropException):
    def __init__(self, resource: str, id: int):
        super().__init__(f"{resource} with id={id} not found", status_code=404)


class UnauthorizedError(FusionDropException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(detail, status_code=401)


class BadRequestError(FusionDropException):
    def __init__(self, detail: str):
        super().__init__(detail, status_code=400)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(FusionDropException)
    async def app_exception_handler(request: Request, exc: FusionDropException):
        logger.warning("app_exception", path=request.url.path,
                       status=exc.status_code, message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "type": type(exc).__name__},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning("http_exception", path=request.url.path,
                       status=exc.status_code, detail=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning("validation_error", path=request.url.path, errors=exc.errors())
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "type": "ValidationError"},
        )
# backend/middleware/request_id.py
import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.utils.request_context import request_id_ctx


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Assigns a request ID and tracks basic performance for every HTTP request.

    - Accepts incoming X-Request-ID header if present (useful for tracing
      across proxies / mobile apps).
    - Otherwise generates a UUID4.
    - Stores it in contextvar for logging.
    - Adds X-Request-ID and X-Process-Time headers to the response.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable):
        incoming_rid = request.headers.get("X-Request-ID")
        request_id = incoming_rid or str(uuid.uuid4())

        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            process_time = time.perf_counter() - start
            request_id_ctx.reset(token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response
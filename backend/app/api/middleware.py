"""Request ID, structured access logs, security headers and a simple per-client rate limiter."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config.logging import request_id_var

logger = logging.getLogger("signalroom.access")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=(self)",
    "Cross-Origin-Opener-Policy": "same-origin",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        if request.url.path.startswith("/api/v1/") and "cache-control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
        if not request.url.path.endswith("/live"):
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "elapsed_ms": int((time.perf_counter() - started) * 1000),
                },
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limiter per client (Authorization token hash or IP). Per process: production
    would add AWS WAF rate-based rules in front of CloudFront/ALB."""

    def __init__(self, app: ASGIApp, per_minute: int = 120) -> None:
        super().__init__(app)
        self._limit = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if (
            not path.startswith("/api/v1/")
            or path.startswith("/api/v1/health")
            or path.endswith("/events")
            or "/local-storage/" in path
        ):
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        client = request.client.host if request.client else "unknown"
        key = str(hash(auth)) if auth else client
        now = time.monotonic()
        with self._lock:
            window = self._hits[key]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= self._limit:
                retry = int(60 - (now - window[0])) + 1
                return JSONResponse(
                    {
                        "error": "rate_limited",
                        "message": "Too many requests. Please slow down.",
                        "request_id": request_id_var.get(),
                    },
                    status_code=429,
                    headers={"Retry-After": str(retry)},
                )
            window.append(now)
        return await call_next(request)

"""FastAPI application factory. API: `uvicorn app.main:app`."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.api.router import api_router
from app.config.logging import configure_logging, request_id_var
from app.container import get_container
from app.services.errors import ServiceError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = get_container()
    worker = None
    s = container.settings
    if s.backend_mode == "local" and s.local_worker_enabled and s.app_env != "test":
        from app.workers.local_worker import LocalWorkerThread

        worker = LocalWorkerThread(container)
        worker.start()
    logger.info(
        "api_started", extra={"backend": s.backend_mode, "auth": s.auth_mode, "ai": container.ai.describe()}
    )
    yield
    if worker:
        worker.stop()


def create_app() -> FastAPI:
    settings = get_container().settings
    configure_logging(settings.log_level)
    app = FastAPI(
        title="SignalRoom AI API",
        version="0.1.0",
        description="Know what moved the market. Know why. — multimodal multi-agent financial research API (educational prototype).",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(RateLimitMiddleware, per_minute=settings.rate_limit_per_minute)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Last-Event-ID", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(ServiceError)
    async def service_error(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            {"error": exc.code, "message": exc.message, "request_id": request_id_var.get()},
            status_code=exc.status_code,
        )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            {"error": "http_error", "message": str(exc.detail), "request_id": request_id_var.get()},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
        return JSONResponse(
            {
                "error": "validation_failed",
                "message": f"{field}: {first.get('msg', 'invalid value')}",
                "request_id": request_id_var.get(),
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", extra={"error_type": type(exc).__name__})
        return JSONResponse(
            {
                "error": "internal_error",
                "message": "Something went wrong on our side. Please retry.",
                "request_id": request_id_var.get(),
            },
            status_code=500,
        )

    app.include_router(api_router)
    return app


app = create_app()

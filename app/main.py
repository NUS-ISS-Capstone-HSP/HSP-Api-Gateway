from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.errors import AppError, build_error_response, map_grpc_error
from app.gateway.grpc_clients import GatewayGrpcClients
from app.gateway.http_to_rpc_router import router as gateway_router
from app.middleware.auth import AuthMiddleware
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger("hsp_gateway")


def _configure_logging() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="hsp-api-gateway",
        version="1.0.0",
        description="HTTP -> gRPC API Gateway",
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    app.openapi_schema = schema
    return app.openapi_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.grpc_clients = GatewayGrpcClients(settings)
    yield
    await app.state.grpc_clients.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    _configure_logging()

    app = FastAPI(title="hsp-api-gateway", lifespan=lifespan)
    resolved_settings = settings or get_settings()

    app.add_middleware(AuthMiddleware, settings=resolved_settings)
    app.add_middleware(RequestIDMiddleware)

    @app.middleware("http")
    async def access_log_middleware(request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)

        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        request_id = getattr(request.state, "request_id", "-")
        identity = getattr(request.state, "identity", None)
        user_id = identity.user_id if identity else None

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "user_id": user_id,
                },
                ensure_ascii=False,
            )
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_response(code=exc.code, message=exc.message, request_id=request_id),
        )

    @app.exception_handler(grpc.RpcError)
    async def grpc_error_handler(request: Request, exc: grpc.RpcError) -> JSONResponse:
        mapped = map_grpc_error(exc)
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=mapped.status_code,
            content=build_error_response(code=mapped.code, message=mapped.message, request_id=request_id),
        )

    @app.exception_handler(Exception)
    async def fallback_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                code="INTERNAL_ERROR",
                message="Internal server error",
                request_id=request_id,
            ),
        )

    app.include_router(gateway_router)
    app.openapi = lambda: _custom_openapi(app)
    return app


app = create_app()

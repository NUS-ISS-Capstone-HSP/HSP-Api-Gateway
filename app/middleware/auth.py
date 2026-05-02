from __future__ import annotations

import uuid

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import Settings
from app.errors import AppError, build_error_response
from app.security.jwt_utils import IdentityContext, decode_and_validate_jwt

PUBLIC_PATHS = {
    "/healthz",
    "/docs",
    "/docs/oauth2-redirect",
    "/openapi.json",
    "/redoc",
    "/api/users/v1/auth/register",
    "/api/users/v1/auth/login",
}


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        try:
            normalized_path = _normalize_path(request.url.path)

            if normalized_path in PUBLIC_PATHS:
                request.state.identity = None
                return await call_next(request)

            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                raise AppError(code="AUTH_REQUIRED", message="Bearer token is required", status_code=401)

            token = auth_header.removeprefix("Bearer ").strip()
            if not token:
                raise AppError(code="AUTH_REQUIRED", message="Bearer token is required", status_code=401)

            identity = decode_and_validate_jwt(token=token, settings=self.settings)
            _check_rbac(normalized_path, identity)
            request.state.identity = identity

            return await call_next(request)
        except AppError as exc:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            return JSONResponse(
                status_code=exc.status_code,
                content=build_error_response(code=exc.code, message=exc.message, request_id=request_id),
            )


def _normalize_path(path: str) -> str:
    normalized = path.rstrip("/")
    return normalized or "/"


def _check_rbac(path: str, identity: IdentityContext) -> None:
    role = identity.role.upper()

    if path.startswith("/api/users/v1/admin") and role == "WORKER":
        raise AppError(code="FORBIDDEN", message="WORKER cannot access admin endpoints", status_code=403)

    if path == "/api/users/v1/orders/dispatch" and role not in {"CUSTOMER_SERVICE", "OWNER"}:
        raise AppError(code="FORBIDDEN", message="Role cannot dispatch orders", status_code=403)

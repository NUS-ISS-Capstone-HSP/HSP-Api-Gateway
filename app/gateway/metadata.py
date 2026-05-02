from __future__ import annotations

import uuid

from fastapi import Request

from app.security.jwt_utils import IdentityContext

SPOOFABLE_HEADERS = {
    "x-user-id",
    "x-user-email",
    "x-user-role",
    "x-request-id",
    "x-auth-source",
}


def build_gateway_metadata(request: Request) -> tuple[tuple[str, str], ...]:
    identity: IdentityContext | None = getattr(request.state, "identity", None)
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    return (
        ("x-user-id", identity.user_id if identity else "anonymous"),
        ("x-user-email", identity.email if identity else "anonymous@local"),
        ("x-user-role", identity.role if identity else "ANONYMOUS"),
        ("x-request-id", request_id),
        ("x-auth-source", "gateway"),
    )

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any

import jwt
from jwt import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    MissingRequiredClaimError,
)

from app.config import Settings
from app.errors import AppError

logger = logging.getLogger("hsp_gateway")


@dataclass(slots=True)
class IdentityContext:
    user_id: str
    email: str
    role: str


def decode_and_validate_jwt(
    token: str,
    settings: Settings,
    request_id: str | None = None,
    path: str | None = None,
) -> IdentityContext:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": ["exp", "iss", "aud", "sub", "email", "role"],
            },
        )
    except ExpiredSignatureError as exc:
        _log_jwt_failure(
            reason="expired",
            token=token,
            settings=settings,
            exc=exc,
            request_id=request_id,
            path=path,
        )
        raise AppError(code="TOKEN_EXPIRED", message="Token has expired", status_code=401) from exc
    except MissingRequiredClaimError as exc:
        _log_jwt_failure(
            reason="missing_required_claim",
            token=token,
            settings=settings,
            exc=exc,
            request_id=request_id,
            path=path,
        )
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc
    except InvalidIssuerError as exc:
        _log_jwt_failure(
            reason="invalid_issuer",
            token=token,
            settings=settings,
            exc=exc,
            request_id=request_id,
            path=path,
        )
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc
    except InvalidAudienceError as exc:
        _log_jwt_failure(
            reason="invalid_audience",
            token=token,
            settings=settings,
            exc=exc,
            request_id=request_id,
            path=path,
        )
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc
    except InvalidSignatureError as exc:
        _log_jwt_failure(
            reason="invalid_signature",
            token=token,
            settings=settings,
            exc=exc,
            request_id=request_id,
            path=path,
        )
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc
    except DecodeError as exc:
        _log_jwt_failure(
            reason="decode_error",
            token=token,
            settings=settings,
            exc=exc,
            request_id=request_id,
            path=path,
        )
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc
    except InvalidTokenError as exc:
        _log_jwt_failure(
            reason="invalid_token",
            token=token,
            settings=settings,
            exc=exc,
            request_id=request_id,
            path=path,
        )
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc
    except Exception as exc:
        _log_jwt_failure(
            reason="unexpected_jwt_error",
            token=token,
            settings=settings,
            exc=exc,
            request_id=request_id,
            path=path,
        )
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc

    return IdentityContext(
        user_id=str(claims["sub"]),
        email=str(claims["email"]),
        role=str(claims["role"]),
    )


def _log_jwt_failure(
    reason: str,
    token: str,
    settings: Settings,
    exc: Exception,
    request_id: str | None,
    path: str | None,
) -> None:
    header, claims = _extract_unverified_token_details(token)
    logger.warning(
        json.dumps(
            {
                "event": "jwt_validation_failed",
                "reason": reason,
                "request_id": request_id or "-",
                "path": path or "-",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "expected_issuer": settings.jwt_issuer,
                "expected_audience": settings.jwt_audience,
                "token_preview": _token_preview(token),
                "token_length": len(token),
                "header_alg": header.get("alg"),
                "header_typ": header.get("typ"),
                "claim_iss": claims.get("iss"),
                "claim_aud": claims.get("aud"),
                "claim_sub": claims.get("sub"),
                "claim_role": claims.get("role"),
                "claim_exp": claims.get("exp"),
            },
            ensure_ascii=False,
        )
    )


def _extract_unverified_token_details(token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        header = {}

    try:
        claims = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
        if not isinstance(claims, dict):
            claims = {}
    except Exception:
        claims = {}

    return header, claims


def _token_preview(token: str) -> str:
    if len(token) <= 16:
        return token
    return f"{token[:8]}...{token[-8:]}"

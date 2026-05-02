from __future__ import annotations

from dataclasses import dataclass

import jwt
from jwt import DecodeError, ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, InvalidSignatureError

from app.config import Settings
from app.errors import AppError


@dataclass(slots=True)
class IdentityContext:
    user_id: str
    email: str
    role: str


def decode_and_validate_jwt(token: str, settings: Settings) -> IdentityContext:
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
        raise AppError(code="TOKEN_EXPIRED", message="Token has expired", status_code=401) from exc
    except (InvalidIssuerError, InvalidAudienceError, InvalidSignatureError, DecodeError) as exc:
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc
    except Exception as exc:
        raise AppError(code="TOKEN_INVALID", message="Token is invalid", status_code=401) from exc

    return IdentityContext(
        user_id=str(claims["sub"]),
        email=str(claims["email"]),
        role=str(claims["role"]),
    )

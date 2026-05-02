from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus

import grpc


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int


GRPC_STATUS_TO_HTTP: dict[grpc.StatusCode, int] = {
    grpc.StatusCode.INVALID_ARGUMENT: HTTPStatus.BAD_REQUEST,
    grpc.StatusCode.UNAUTHENTICATED: HTTPStatus.UNAUTHORIZED,
    grpc.StatusCode.PERMISSION_DENIED: HTTPStatus.FORBIDDEN,
    grpc.StatusCode.NOT_FOUND: HTTPStatus.NOT_FOUND,
    grpc.StatusCode.ALREADY_EXISTS: HTTPStatus.CONFLICT,
    grpc.StatusCode.FAILED_PRECONDITION: HTTPStatus.BAD_REQUEST,
    grpc.StatusCode.RESOURCE_EXHAUSTED: HTTPStatus.TOO_MANY_REQUESTS,
    grpc.StatusCode.UNIMPLEMENTED: HTTPStatus.NOT_IMPLEMENTED,
    grpc.StatusCode.UNAVAILABLE: HTTPStatus.SERVICE_UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED: HTTPStatus.GATEWAY_TIMEOUT,
}


def build_error_response(code: str, message: str, request_id: str) -> dict[str, str]:
    return {
        "code": code,
        "message": message,
        "request_id": request_id,
    }


def map_grpc_error(exc: grpc.RpcError) -> AppError:
    status = exc.code() if hasattr(exc, "code") else None
    message = exc.details() if hasattr(exc, "details") else None

    if isinstance(status, grpc.StatusCode):
        http_status = int(GRPC_STATUS_TO_HTTP.get(status, HTTPStatus.BAD_GATEWAY))
        code = f"GRPC_{status.name}"
    else:
        http_status = int(HTTPStatus.BAD_GATEWAY)
        code = "GRPC_UNKNOWN"

    return AppError(
        code=code,
        message=message or "Downstream gRPC service returned an error",
        status_code=http_status,
    )

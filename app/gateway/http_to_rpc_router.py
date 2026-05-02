from __future__ import annotations

from typing import Any, Awaitable, Callable

import grpc
from fastapi import APIRouter, Query, Request

from app.errors import map_grpc_error
from app.gateway.grpc_clients import GatewayGrpcClients
from app.gateway.metadata import build_gateway_metadata
from app.schemas.user import (
    DispatchOrderRequestModel,
    GetMeResponseModel,
    LoginRequestModel,
    LoginResponseModel,
    MessageResponseModel,
    RegisterRequestModel,
    RegisterResponseModel,
)
from app.schemas.order import (
    CreateOrderRequestModel,
    CreateOrderResponseModel,
    GetOrderResponseModel,
    ListOrdersResponseModel,
    UpdateOrderStatusBodyModel,
    UpdateOrderStatusResponseModel,
)
from app.schemas.dispatch import (
    ConfirmWorkerResponseRequestModel,
    ConfirmWorkerResponseResponseModel,
    GetOrderDispatchHistoryResponseModel,
    ListAvailableWorkersResponseModel,
    ListWorkerPendingDispatchesResponseModel,
    ManualAssignOrderRequestModel,
    ManualAssignOrderResponseModel,
)
from app.schemas.worker_schedule import (
    GetOrderDetailResponseModel,
    ListDailyScheduleResponseModel,
    ListWorkersResponseModel,
    RegisterWorkerRequestModel,
    RegisterWorkerResponseModel,
    SyncOrderEventRequestModel,
    SyncOrderEventResponseModel,
    UpdateWorkerStatusBodyModel,
    UpdateWorkerStatusResponseModel,
)

router = APIRouter()


def _get_clients(request: Request) -> GatewayGrpcClients:
    return request.app.state.grpc_clients


async def _invoke_rpc(call: Callable[..., Awaitable[dict[str, Any]]], *args, **kwargs) -> dict[str, Any]:
    try:
        return await call(*args, **kwargs)
    except grpc.RpcError as exc:
        raise map_grpc_error(exc) from exc


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/users/v1/auth/register", response_model=RegisterResponseModel, tags=["User"])
async def register(payload: RegisterRequestModel, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.user_register, payload.model_dump(), metadata)


@router.post("/api/users/v1/auth/login", response_model=LoginResponseModel, tags=["User"])
async def login(payload: LoginRequestModel, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.user_login, payload.model_dump(), metadata)


@router.get(
    "/api/users/v1/profile",
    response_model=GetMeResponseModel,
    tags=["User"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def get_profile(request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    payload = {"query": dict(request.query_params)}
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.user_profile, payload, metadata)


@router.get(
    "/api/users/v1/admin/ping",
    response_model=MessageResponseModel,
    tags=["User"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def admin_ping(request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    payload: dict[str, Any] = {}
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.user_admin_ping, payload, metadata)


@router.post(
    "/api/users/v1/orders/dispatch",
    response_model=MessageResponseModel,
    tags=["User"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def dispatch_order(payload: DispatchOrderRequestModel, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.user_dispatch, payload.model_dump(exclude_none=True), metadata)


@router.post(
    "/api/orders/v1/orders",
    response_model=CreateOrderResponseModel,
    tags=["Order"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def create_order(payload: CreateOrderRequestModel, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.order_create, payload.model_dump(), metadata)


@router.get(
    "/api/orders/v1/orders/{order_id}",
    response_model=GetOrderResponseModel,
    tags=["Order"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def get_order(order_id: str, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.order_get, {"order_id": order_id}, metadata)


@router.get(
    "/api/orders/v1/orders",
    response_model=ListOrdersResponseModel,
    tags=["Order"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def list_orders(
    request: Request,
    customer_name: str | None = Query(default=None),
    service_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    payload = {
        "customer_name": customer_name,
        "service_type": service_type,
        "status": status,
        "page": page,
        "page_size": page_size,
    }
    return await _invoke_rpc(clients.order_list, payload, metadata)


@router.patch(
    "/api/orders/v1/orders/{order_id}/status",
    response_model=UpdateOrderStatusResponseModel,
    tags=["Order"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def update_order_status(
    order_id: str,
    payload: UpdateOrderStatusBodyModel,
    request: Request,
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    body = payload.model_dump(exclude_none=True)
    body["order_id"] = order_id
    return await _invoke_rpc(clients.order_update_status, body, metadata)


@router.get(
    "/api/dispatch/v1/workers/available",
    response_model=ListAvailableWorkersResponseModel,
    tags=["Dispatch"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def list_available_workers(
    request: Request,
    service_type: str | None = Query(default=None),
    region: str | None = Query(default=None),
    at_time: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    payload = {
        "service_type": service_type,
        "region": region,
        "at_time": at_time,
        "limit": limit,
    }
    return await _invoke_rpc(clients.dispatch_list_available_workers, payload, metadata)


@router.post(
    "/api/dispatch/v1/assignments/manual",
    response_model=ManualAssignOrderResponseModel,
    tags=["Dispatch"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def manual_assign_order(payload: ManualAssignOrderRequestModel, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.dispatch_manual_assign, payload.model_dump(), metadata)


@router.get(
    "/api/dispatch/v1/worker/pending-dispatches",
    response_model=ListWorkerPendingDispatchesResponseModel,
    tags=["Dispatch"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def list_worker_pending_dispatches(request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.dispatch_list_worker_pending, {}, metadata)


@router.post(
    "/api/dispatch/v1/dispatches/{dispatch_id}/confirm",
    response_model=ConfirmWorkerResponseResponseModel,
    tags=["Dispatch"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def confirm_worker_response(
    dispatch_id: str,
    payload: ConfirmWorkerResponseRequestModel,
    request: Request,
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    body = payload.model_dump(exclude_none=True)
    body["dispatch_id"] = dispatch_id
    return await _invoke_rpc(clients.dispatch_confirm_worker_response, body, metadata)


@router.get(
    "/api/dispatch/v1/orders/{order_id}/history",
    response_model=GetOrderDispatchHistoryResponseModel,
    tags=["Dispatch"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def get_order_dispatch_history(order_id: str, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.dispatch_order_history, {"order_id": order_id}, metadata)


@router.post(
    "/api/worker-schedule/v1/workers/register",
    response_model=RegisterWorkerResponseModel,
    tags=["WorkerSchedule"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def worker_schedule_register_worker(payload: RegisterWorkerRequestModel, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.worker_schedule_register_worker, payload.model_dump(), metadata)


@router.get(
    "/api/worker-schedule/v1/workers",
    response_model=ListWorkersResponseModel,
    tags=["WorkerSchedule"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def worker_schedule_list_workers(request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.worker_schedule_list_workers, {}, metadata)


@router.patch(
    "/api/worker-schedule/v1/workers/{worker_id}/status",
    response_model=UpdateWorkerStatusResponseModel,
    tags=["WorkerSchedule"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def worker_schedule_update_worker_status(
    worker_id: str,
    payload: UpdateWorkerStatusBodyModel,
    request: Request,
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    body = payload.model_dump(exclude_none=True)
    body["worker_id"] = worker_id
    return await _invoke_rpc(clients.worker_schedule_update_worker_status, body, metadata)


@router.post(
    "/api/worker-schedule/v1/orders/sync-event",
    response_model=SyncOrderEventResponseModel,
    tags=["WorkerSchedule"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def worker_schedule_sync_order_event(payload: SyncOrderEventRequestModel, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.worker_schedule_sync_order_event, payload.model_dump(), metadata)


@router.get(
    "/api/worker-schedule/v1/schedule/daily",
    response_model=ListDailyScheduleResponseModel,
    tags=["WorkerSchedule"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def worker_schedule_list_daily(
    request: Request,
    date: str = Query(..., description="日期，例如 2026-04-07"),
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.worker_schedule_list_daily, {"date": date}, metadata)


@router.get(
    "/api/worker-schedule/v1/orders/{order_id}",
    response_model=GetOrderDetailResponseModel,
    tags=["WorkerSchedule"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def worker_schedule_get_order_detail(order_id: str, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.worker_schedule_get_order_detail, {"order_id": order_id}, metadata)


@router.get("/api/finance/v1/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    payload = {
        "invoice_id": invoice_id,
        "query": dict(request.query_params),
    }
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.finance_get_invoice, payload, metadata)

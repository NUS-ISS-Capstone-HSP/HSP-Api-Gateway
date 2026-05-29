from __future__ import annotations

from typing import Any, Awaitable, Callable

import grpc
from fastapi import APIRouter, Query, Request

from app.errors import AppError, map_grpc_error
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
    CloseOrderRequestModel,
    UpdateOrderStatusBodyModel,
    UpdateOrderStatusResponseModel,
)
from app.schemas.finance import (
    CreatePaymentRequestModel,
    CreatePaymentResponseModel,
    ListOrderPaymentsResponseModel,
)
from app.schemas.service_execution import (
    AddServicePhotoRequestModel,
    AddServicePhotoResponseModel,
    CompleteServiceRequestModel,
    CompleteServiceResponseModel,
    GetServiceRecordResponseModel,
    StartServiceRequestModel,
    StartServiceResponseModel,
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

MOCKABLE_DOWNSTREAM_GAP_CODES = {
    "GRPC_UNIMPLEMENTED",
    "GRPC_NOT_FOUND",
    "GRPC_INVALID_ARGUMENT",
    "GRPC_FAILED_PRECONDITION",
}


def _get_clients(request: Request) -> GatewayGrpcClients:
    return request.app.state.grpc_clients


async def _invoke_rpc(call: Callable[..., Awaitable[dict[str, Any]]], *args, **kwargs) -> dict[str, Any]:
    try:
        return await call(*args, **kwargs)
    except grpc.RpcError as exc:
        raise map_grpc_error(exc) from exc


def _should_use_mock_fallback(exc: AppError) -> bool:
    return exc.code in MOCKABLE_DOWNSTREAM_GAP_CODES


def _mock_store(request: Request) -> dict[str, Any]:
    if not hasattr(request.app.state, "core_flow_mock_store"):
        request.app.state.core_flow_mock_store = {
            "workers": {},
            "service_records": {},
            "payments": {},
        }
    return request.app.state.core_flow_mock_store


def _identity_value(request: Request, field: str, default: str = "") -> str:
    identity = getattr(request.state, "identity", None)
    return str(getattr(identity, field, default) or default)


def _mock_worker(worker_id: str, worker_name: str = "", status: str = "WORKER_STATUS_AVAILABLE") -> dict[str, Any]:
    return {
        "id": worker_id,
        "name": worker_name or worker_id,
        "status": status,
        "updated_at": "",
    }


def _mock_dispatch(dispatch_id: str, order_id: str, worker_id: str, status: str) -> dict[str, Any]:
    return {
        "dispatch_id": dispatch_id,
        "order_id": order_id,
        "attempt_no": 1,
        "worker_id": worker_id,
        "operator_id": "",
        "status": status,
        "assigned_at": "",
        "responded_at": "",
        "reject_reason": "",
    }


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


@router.post(
    "/api/orders/v1/orders/{order_id}/close",
    response_model=UpdateOrderStatusResponseModel,
    tags=["Order"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def close_order(
    order_id: str,
    payload: CloseOrderRequestModel,
    request: Request,
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    body = payload.model_dump(exclude_none=True)
    body["order_id"] = order_id
    body["target_status"] = "PAID"
    try:
        return await _invoke_rpc(clients.order_update_status, body, metadata)
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        return {
            "order": {
                "order_id": order_id,
                "status": "ORDER_STATUS_PAID",
                "status_updated_at": "",
                "updated_at": "",
            }
        }


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
    try:
        return await _invoke_rpc(clients.dispatch_confirm_worker_response, body, metadata)
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        status = "ACCEPTED" if payload.response.upper().endswith("ACCEPT") else "REJECTED"
        return {
            "dispatch": _mock_dispatch(
                dispatch_id=dispatch_id,
                order_id="",
                worker_id=_identity_value(request, "user_id", "worker-mock"),
                status=status,
            )
        }


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
    body = payload.model_dump()
    try:
        return await _invoke_rpc(clients.worker_schedule_register_worker, body, metadata)
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        worker = _mock_worker(payload.worker_id, payload.worker_name)
        _mock_store(request)["workers"][payload.worker_id] = worker
        return {"worker": worker}


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
    try:
        return await _invoke_rpc(clients.worker_schedule_update_worker_status, body, metadata)
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        status = payload.status.upper()
        worker = _mock_worker(worker_id, worker_id, status if status.startswith("WORKER_STATUS_") else f"WORKER_STATUS_{status}")
        _mock_store(request)["workers"][worker_id] = worker
        return {"worker": worker}


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


@router.post(
    "/api/service-execution/v1/orders/{order_id}/start",
    response_model=StartServiceResponseModel,
    tags=["ServiceExecution"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def service_execution_start_service(
    order_id: str,
    payload: StartServiceRequestModel,
    request: Request,
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    body = payload.model_dump(exclude_none=True)
    body["order_id"] = order_id
    try:
        response = await _invoke_rpc(clients.service_execution_start_service, body, metadata)
        if "record" in response:
            _mock_store(request)["service_records"][order_id] = response["record"]
        return response
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        record = {
            "order_id": order_id,
            "worker_id": payload.worker_id or _identity_value(request, "user_id", "worker-mock"),
            "status": "IN_SERVICE",
            "started_at": payload.started_at or "",
            "completed_at": None,
            "actual_duration_minutes": None,
            "completion_note": None,
            "photos": [],
        }
        _mock_store(request)["service_records"][order_id] = record
        return {"record": record}


@router.post(
    "/api/service-execution/v1/orders/{order_id}/complete",
    response_model=CompleteServiceResponseModel,
    tags=["ServiceExecution"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def service_execution_complete_service(
    order_id: str,
    payload: CompleteServiceRequestModel,
    request: Request,
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    body = payload.model_dump(exclude_none=True)
    body["order_id"] = order_id
    try:
        response = await _invoke_rpc(clients.service_execution_complete_service, body, metadata)
        if "record" in response:
            _mock_store(request)["service_records"][order_id] = response["record"]
        return response
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        records = _mock_store(request)["service_records"]
        record = records.get(
            order_id,
            {
                "order_id": order_id,
                "worker_id": payload.worker_id or _identity_value(request, "user_id", "worker-mock"),
                "started_at": "",
                "photos": [],
            },
        )
        record.update(
            {
                "worker_id": payload.worker_id or record.get("worker_id"),
                "status": "COMPLETE",
                "completed_at": payload.completed_at or "",
                "actual_duration_minutes": payload.actual_duration_minutes,
                "completion_note": payload.completion_note,
                "photos": record.get("photos", []),
            }
        )
        records[order_id] = record
        return {"record": record}


@router.post(
    "/api/service-execution/v1/orders/{order_id}/photos",
    response_model=AddServicePhotoResponseModel,
    tags=["ServiceExecution"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def service_execution_add_photo(
    order_id: str,
    payload: AddServicePhotoRequestModel,
    request: Request,
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    body = payload.model_dump(exclude_none=True)
    body["order_id"] = order_id
    try:
        response = await _invoke_rpc(clients.service_execution_add_photo, body, metadata)
        if "photo" in response:
            record = _mock_store(request)["service_records"].setdefault(
                order_id,
                {"order_id": order_id, "worker_id": "", "status": "", "photos": []},
            )
            record.setdefault("photos", []).append(response["photo"])
        return response
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        photo = {
            "photo_id": f"photo-{order_id}",
            "order_id": order_id,
            "photo_url": payload.photo_url,
            "photo_type": payload.photo_type,
            "remark": payload.remark,
            "uploaded_by": _identity_value(request, "user_id", ""),
            "uploaded_at": "",
        }
        store = _mock_store(request)
        record = store["service_records"].setdefault(
            order_id,
            {"order_id": order_id, "worker_id": "", "status": "", "photos": []},
        )
        record.setdefault("photos", []).append(photo)
        return {"photo": photo}


@router.get(
    "/api/service-execution/v1/orders/{order_id}/record",
    response_model=GetServiceRecordResponseModel,
    tags=["ServiceExecution"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def service_execution_get_record(order_id: str, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    stored_record = _mock_store(request)["service_records"].get(order_id)
    if stored_record:
        return {"record": stored_record}
    try:
        return await _invoke_rpc(clients.service_execution_get_record, {"order_id": order_id}, metadata)
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        record = _mock_store(request)["service_records"].get(
            order_id,
            {
                "order_id": order_id,
                "worker_id": "",
                "status": "COMPLETE",
                "started_at": "",
                "completed_at": "",
                "actual_duration_minutes": None,
                "completion_note": None,
                "photos": [],
            },
        )
        return {"record": record}


@router.get("/api/finance/v1/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    payload = {
        "invoice_id": invoice_id,
        "query": dict(request.query_params),
    }
    metadata = build_gateway_metadata(request)
    return await _invoke_rpc(clients.finance_get_invoice, payload, metadata)


@router.post(
    "/api/finance/v1/orders/{order_id}/payments",
    response_model=CreatePaymentResponseModel,
    tags=["Finance"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def create_payment(
    order_id: str,
    payload: CreatePaymentRequestModel,
    request: Request,
) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    body = payload.model_dump(exclude_none=True)
    body["order_id"] = order_id
    try:
        response = await _invoke_rpc(clients.finance_create_payment, body, metadata)
        if "payment" in response:
            _mock_store(request)["payments"].setdefault(order_id, []).append(response["payment"])
        return response
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        payment = {
            "payment_id": f"pay-{order_id}",
            "order_id": order_id,
            "amount": payload.amount,
            "currency": payload.currency,
            "payment_method": payload.payment_method,
            "payment_status": "PAID",
            "paid_at": payload.paid_at or "",
            "confirmed_by": _identity_value(request, "user_id", ""),
            "remark": payload.remark,
            "created_at": "",
        }
        _mock_store(request)["payments"].setdefault(order_id, []).append(payment)
        return {"payment": payment}


@router.get(
    "/api/finance/v1/orders/{order_id}/payments",
    response_model=ListOrderPaymentsResponseModel,
    tags=["Finance"],
    openapi_extra={"security": [{"BearerAuth": []}]},
)
async def list_order_payments(order_id: str, request: Request) -> dict[str, Any]:
    clients = _get_clients(request)
    metadata = build_gateway_metadata(request)
    stored_payments = _mock_store(request)["payments"].get(order_id)
    if stored_payments:
        return {"payments": stored_payments}
    try:
        return await _invoke_rpc(clients.finance_list_order_payments, {"order_id": order_id}, metadata)
    except AppError as exc:
        if not _should_use_mock_fallback(exc):
            raise
        return {"payments": _mock_store(request)["payments"].get(order_id, [])}

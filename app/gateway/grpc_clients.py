from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

import grpc
from google.protobuf import json_format, struct_pb2

from app.config import Settings

_GENERATED_DIR = Path(__file__).resolve().parents[2] / "generated"
if str(_GENERATED_DIR) not in sys.path:
    sys.path.append(str(_GENERATED_DIR))

import user_pb2
import user_pb2_grpc
import order_pb2
import order_pb2_grpc
import dispatch_pb2
import dispatch_pb2_grpc
import worker_schedule_pb2
import worker_schedule_pb2_grpc

GrpcMetadata = tuple[tuple[str, str], ...]
logger = logging.getLogger("hsp_gateway")

_ROLE_NAME_TO_ENUM = {
    "WORKER": user_pb2.USER_ROLE_WORKER,
    "CUSTOMER_SERVICE": user_pb2.USER_ROLE_CUSTOMER_SERVICE,
    "OWNER": user_pb2.USER_ROLE_OWNER,
}

_SERVICE_TYPE_NAME_TO_ENUM = {
    "CLEANING": order_pb2.SERVICE_TYPE_CLEANING,
    "REPAIR": order_pb2.SERVICE_TYPE_REPAIR,
    "INSTALL": order_pb2.SERVICE_TYPE_INSTALL,
    "OTHER": order_pb2.SERVICE_TYPE_OTHER,
}

_ORDER_STATUS_NAME_TO_ENUM = {
    "CREATED": order_pb2.ORDER_STATUS_CREATED,
    "PENDING": order_pb2.ORDER_STATUS_PENDING,
    "ACCEPT": order_pb2.ORDER_STATUS_ACCEPT,
    "COMPLETE": order_pb2.ORDER_STATUS_COMPLETE,
    "PAID": order_pb2.ORDER_STATUS_PAID,
}

_WORKER_RESPONSE_NAME_TO_ENUM = {
    "ACCEPT": dispatch_pb2.WORKER_RESPONSE_TYPE_ACCEPT,
    "REJECT": dispatch_pb2.WORKER_RESPONSE_TYPE_REJECT,
}

_WORKER_SCHEDULE_STATUS_NAME_TO_ENUM = {
    "AVAILABLE": worker_schedule_pb2.WORKER_STATUS_AVAILABLE,
    "ASSIGNED": worker_schedule_pb2.WORKER_STATUS_ASSIGNED,
    "IN_SERVICE": worker_schedule_pb2.WORKER_STATUS_IN_SERVICE,
}

_ORDER_EVENT_TYPE_NAME_TO_ENUM = {
    "ASSIGNED": worker_schedule_pb2.ORDER_EVENT_TYPE_ASSIGNED,
    "SERVICE_STARTED": worker_schedule_pb2.ORDER_EVENT_TYPE_SERVICE_STARTED,
    "COMPLETED": worker_schedule_pb2.ORDER_EVENT_TYPE_COMPLETED,
    "CANCELED": worker_schedule_pb2.ORDER_EVENT_TYPE_CANCELED,
}


def _serialize_struct(payload: dict[str, Any]) -> bytes:
    struct_message = struct_pb2.Struct()
    struct_message.update(payload)
    return struct_message.SerializeToString()


def _deserialize_struct(raw: bytes) -> dict[str, Any]:
    struct_message = struct_pb2.Struct()
    struct_message.ParseFromString(raw)
    return json_format.MessageToDict(struct_message, preserving_proto_field_name=True)


def _message_to_dict(message) -> dict[str, Any]:
    return json_format.MessageToDict(
        message,
        preserving_proto_field_name=True,
        use_integers_for_enums=False,
    )


def _parse_user_role(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.upper().strip()
        if normalized in _ROLE_NAME_TO_ENUM:
            return _ROLE_NAME_TO_ENUM[normalized]
        if normalized.startswith("USER_ROLE_"):
            try:
                return user_pb2.UserRole.Value(normalized)
            except ValueError:
                return user_pb2.USER_ROLE_UNSPECIFIED
    return user_pb2.USER_ROLE_UNSPECIFIED


def _parse_service_type(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.upper().strip()
        if normalized in _SERVICE_TYPE_NAME_TO_ENUM:
            return _SERVICE_TYPE_NAME_TO_ENUM[normalized]
        if normalized.startswith("SERVICE_TYPE_"):
            try:
                return order_pb2.ServiceType.Value(normalized)
            except ValueError:
                return order_pb2.SERVICE_TYPE_UNSPECIFIED
    return order_pb2.SERVICE_TYPE_UNSPECIFIED


def _parse_order_status(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.upper().strip()
        if normalized in _ORDER_STATUS_NAME_TO_ENUM:
            return _ORDER_STATUS_NAME_TO_ENUM[normalized]
        if normalized.startswith("ORDER_STATUS_"):
            try:
                return order_pb2.OrderStatus.Value(normalized)
            except ValueError:
                return order_pb2.ORDER_STATUS_UNSPECIFIED
    return order_pb2.ORDER_STATUS_UNSPECIFIED


def _parse_worker_response_type(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.upper().strip()
        if normalized in _WORKER_RESPONSE_NAME_TO_ENUM:
            return _WORKER_RESPONSE_NAME_TO_ENUM[normalized]
        if normalized.startswith("WORKER_RESPONSE_TYPE_"):
            try:
                return dispatch_pb2.WorkerResponseType.Value(normalized)
            except ValueError:
                return dispatch_pb2.WORKER_RESPONSE_TYPE_UNSPECIFIED
    return dispatch_pb2.WORKER_RESPONSE_TYPE_UNSPECIFIED


def _parse_worker_schedule_status(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.upper().strip()
        if normalized in _WORKER_SCHEDULE_STATUS_NAME_TO_ENUM:
            return _WORKER_SCHEDULE_STATUS_NAME_TO_ENUM[normalized]
        if normalized.startswith("WORKER_STATUS_"):
            try:
                return worker_schedule_pb2.WorkerStatus.Value(normalized)
            except ValueError:
                return worker_schedule_pb2.WORKER_STATUS_UNSPECIFIED
    return worker_schedule_pb2.WORKER_STATUS_UNSPECIFIED


def _parse_order_event_type(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.upper().strip()
        if normalized in _ORDER_EVENT_TYPE_NAME_TO_ENUM:
            return _ORDER_EVENT_TYPE_NAME_TO_ENUM[normalized]
        if normalized.startswith("ORDER_EVENT_TYPE_"):
            try:
                return worker_schedule_pb2.OrderEventType.Value(normalized)
            except ValueError:
                return worker_schedule_pb2.ORDER_EVENT_TYPE_UNSPECIFIED
    return worker_schedule_pb2.ORDER_EVENT_TYPE_UNSPECIFIED


def _metadata_value(metadata: GrpcMetadata, key: str, default: str = "") -> str:
    lowered = key.lower()
    for k, v in metadata:
        if k.lower() == lowered:
            return v
    return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class GenericGrpcServiceClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str, methods: set[str]):
        self._callers: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {}
        for method in methods:
            method_path = f"/{service_name}/{method}"
            self._callers[method] = channel.unary_unary(
                method_path,
                request_serializer=_serialize_struct,
                response_deserializer=_deserialize_struct,
            )

    async def call(
        self,
        method: str,
        payload: dict[str, Any],
        metadata: GrpcMetadata,
        timeout: float,
    ) -> dict[str, Any]:
        if method not in self._callers:
            raise ValueError(f"Unknown gRPC method: {method}")
        return await self._callers[method](payload, metadata=metadata, timeout=timeout)


class GatewayGrpcClients:
    def __init__(self, settings: Settings):
        self._settings = settings

        self._user_channel = grpc.aio.insecure_channel(settings.user_grpc_target)
        self._order_channel = grpc.aio.insecure_channel(settings.order_grpc_target)
        self._dispatch_channel = grpc.aio.insecure_channel(settings.dispatch_grpc_target)
        self._worker_schedule_channel = grpc.aio.insecure_channel(settings.worker_schedule_grpc_target)
        self._finance_channel = grpc.aio.insecure_channel(settings.finance_grpc_target)

        self._user_client = user_pb2_grpc.UserAuthServiceStub(self._user_channel)
        self._order_client = order_pb2_grpc.OrderServiceStub(self._order_channel)
        self._dispatch_client = dispatch_pb2_grpc.DispatchServiceStub(self._dispatch_channel)
        self._worker_schedule_client = worker_schedule_pb2_grpc.WorkerScheduleServiceStub(self._worker_schedule_channel)
        self._finance_client = GenericGrpcServiceClient(
            self._finance_channel,
            "hsp.finance.v1.FinanceService",
            {"GetInvoice"},
        )

    @property
    def timeout_seconds(self) -> float:
        return self._settings.grpc_timeout_seconds

    async def close(self) -> None:
        await self._user_channel.close()
        await self._order_channel.close()
        await self._dispatch_channel.close()
        await self._worker_schedule_channel.close()
        await self._finance_channel.close()

    def _log_rpc_response(self, rpc_method: str, metadata: GrpcMetadata, response: dict[str, Any]) -> None:
        logger.info(
            json.dumps(
                {
                    "request_id": _metadata_value(metadata, "x-request-id", "-"),
                    "rpc_method": rpc_method,
                    "rpc_response": response,
                },
                ensure_ascii=False,
                default=str,
            )
        )

    async def user_register(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = user_pb2.RegisterRequest(
            email=str(payload.get("email", "")),
            password=str(payload.get("password", "")),
            role=_parse_user_role(payload.get("role")),
            worker_display_name=str(payload.get("worker_display_name", "")),
        )
        response = await self._user_client.Register(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("user.v1.UserAuthService/Register", metadata, response_dict)
        return response_dict

    async def user_login(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = user_pb2.LoginRequest(
            email=str(payload.get("email", "")),
            password=str(payload.get("password", "")),
        )
        response = await self._user_client.Login(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("user.v1.UserAuthService/Login", metadata, response_dict)
        return response_dict

    async def user_profile(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        response = await self._user_client.GetMe(
            user_pb2.GetMeRequest(),
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("user.v1.UserAuthService/GetMe", metadata, response_dict)
        return response_dict

    async def user_admin_ping(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        response = await self._user_client.GetAdminDashboard(
            user_pb2.GetAdminDashboardRequest(),
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("user.v1.UserAuthService/GetAdminDashboard", metadata, response_dict)
        return response_dict

    async def user_dispatch(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        response = await self._user_client.DispatchOrder(
            user_pb2.DispatchOrderRequest(),
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("user.v1.UserAuthService/DispatchOrder", metadata, response_dict)
        return response_dict

    async def order_create(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = order_pb2.CreateOrderRequest(
            customer_name=str(payload.get("customer_name", "")),
            phone=str(payload.get("phone", "")),
            service_address=str(payload.get("service_address", "")),
            service_type=_parse_service_type(payload.get("service_type")),
            appointment_time=str(payload.get("appointment_time", "")),
            estimated_duration_minutes=_safe_int(payload.get("estimated_duration_minutes"), 0),
        )
        response = await self._order_client.CreateOrder(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("order.v1.OrderService/CreateOrder", metadata, response_dict)
        return response_dict

    async def order_get(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = order_pb2.GetOrderRequest(order_id=str(payload.get("order_id", "")))
        response = await self._order_client.GetOrder(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("order.v1.OrderService/GetOrder", metadata, response_dict)
        return response_dict

    async def order_list(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = order_pb2.ListOrdersRequest(
            customer_name=str(payload.get("customer_name", "")),
            service_type=_parse_service_type(payload.get("service_type")),
            status=_parse_order_status(payload.get("status")),
            page=_safe_int(payload.get("page"), 1),
            page_size=_safe_int(payload.get("page_size"), 20),
        )
        response = await self._order_client.ListOrders(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("order.v1.OrderService/ListOrders", metadata, response_dict)
        return response_dict

    async def order_update_status(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = order_pb2.UpdateOrderStatusRequest(
            order_id=str(payload.get("order_id", "")),
            target_status=_parse_order_status(payload.get("target_status")),
            assigned_worker_id=str(payload.get("assigned_worker_id", "")),
        )
        response = await self._order_client.UpdateOrderStatus(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("order.v1.OrderService/UpdateOrderStatus", metadata, response_dict)
        return response_dict

    async def dispatch_list_available_workers(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = dispatch_pb2.ListAvailableWorkersRequest(
            service_type=str(payload.get("service_type") or ""),
            region=str(payload.get("region") or ""),
            at_time=str(payload.get("at_time") or ""),
            limit=_safe_int(payload.get("limit"), 20),
        )
        response = await self._dispatch_client.ListAvailableWorkers(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("dispatch.v1.DispatchService/ListAvailableWorkers", metadata, response_dict)
        return response_dict

    async def dispatch_manual_assign(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = dispatch_pb2.ManualAssignOrderRequest(
            order_id=str(payload.get("order_id", "")),
            worker_id=str(payload.get("worker_id", "")),
        )
        response = await self._dispatch_client.ManualAssignOrder(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("dispatch.v1.DispatchService/ManualAssignOrder", metadata, response_dict)
        return response_dict

    async def dispatch_list_worker_pending(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        response = await self._dispatch_client.ListWorkerPendingDispatches(
            dispatch_pb2.ListWorkerPendingDispatchesRequest(),
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("dispatch.v1.DispatchService/ListWorkerPendingDispatches", metadata, response_dict)
        return response_dict

    async def dispatch_confirm_worker_response(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = dispatch_pb2.ConfirmWorkerResponseRequest(
            dispatch_id=str(payload.get("dispatch_id", "")),
            response=_parse_worker_response_type(payload.get("response")),
            reject_reason=str(payload.get("reject_reason", "")),
        )
        response = await self._dispatch_client.ConfirmWorkerResponse(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("dispatch.v1.DispatchService/ConfirmWorkerResponse", metadata, response_dict)
        return response_dict

    async def dispatch_order_history(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = dispatch_pb2.GetOrderDispatchHistoryRequest(order_id=str(payload.get("order_id", "")))
        response = await self._dispatch_client.GetOrderDispatchHistory(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("dispatch.v1.DispatchService/GetOrderDispatchHistory", metadata, response_dict)
        return response_dict

    async def worker_schedule_register_worker(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = worker_schedule_pb2.RegisterWorkerRequest(
            worker_id=str(payload.get("worker_id", "")),
            worker_name=str(payload.get("worker_name", "")),
        )
        response = await self._worker_schedule_client.RegisterWorker(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("worker_schedule.v1.WorkerScheduleService/RegisterWorker", metadata, response_dict)
        return response_dict

    async def worker_schedule_list_workers(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        response = await self._worker_schedule_client.ListWorkers(
            worker_schedule_pb2.ListWorkersRequest(),
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("worker_schedule.v1.WorkerScheduleService/ListWorkers", metadata, response_dict)
        return response_dict

    async def worker_schedule_update_worker_status(
        self,
        payload: dict[str, Any],
        metadata: GrpcMetadata,
    ) -> dict[str, Any]:
        request = worker_schedule_pb2.UpdateWorkerStatusRequest(
            worker_id=str(payload.get("worker_id", "")),
            status=_parse_worker_schedule_status(payload.get("status")),
        )
        response = await self._worker_schedule_client.UpdateWorkerStatus(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("worker_schedule.v1.WorkerScheduleService/UpdateWorkerStatus", metadata, response_dict)
        return response_dict

    async def worker_schedule_sync_order_event(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = worker_schedule_pb2.SyncOrderEventRequest(
            order_id=str(payload.get("order_id", "")),
            worker_id=str(payload.get("worker_id", "")),
            worker_name=str(payload.get("worker_name", "")),
            event_type=_parse_order_event_type(payload.get("event_type")),
            start_time=str(payload.get("start_time", "")),
            end_time=str(payload.get("end_time", "")),
            title=str(payload.get("title", "")),
        )
        response = await self._worker_schedule_client.SyncOrderEvent(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("worker_schedule.v1.WorkerScheduleService/SyncOrderEvent", metadata, response_dict)
        return response_dict

    async def worker_schedule_list_daily(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = worker_schedule_pb2.ListDailyScheduleRequest(date=str(payload.get("date", "")))
        response = await self._worker_schedule_client.ListDailySchedule(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("worker_schedule.v1.WorkerScheduleService/ListDailySchedule", metadata, response_dict)
        return response_dict

    async def worker_schedule_get_order_detail(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        request = worker_schedule_pb2.GetOrderDetailRequest(order_id=str(payload.get("order_id", "")))
        response = await self._worker_schedule_client.GetOrderDetail(
            request,
            metadata=metadata,
            timeout=self.timeout_seconds,
        )
        response_dict = _message_to_dict(response)
        self._log_rpc_response("worker_schedule.v1.WorkerScheduleService/GetOrderDetail", metadata, response_dict)
        return response_dict

    async def finance_get_invoice(self, payload: dict[str, Any], metadata: GrpcMetadata) -> dict[str, Any]:
        response = await self._finance_client.call("GetInvoice", payload, metadata, self.timeout_seconds)
        self._log_rpc_response("hsp.finance.v1.FinanceService/GetInvoice", metadata, response)
        return response

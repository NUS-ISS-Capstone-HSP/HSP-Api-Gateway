from __future__ import annotations

import asyncio
import os
from typing import Any

import grpc
from google.protobuf import json_format, struct_pb2


def struct_to_dict(message: struct_pb2.Struct) -> dict[str, Any]:
    return json_format.MessageToDict(message, preserving_proto_field_name=True)


def dict_to_struct(payload: dict[str, Any]) -> struct_pb2.Struct:
    message = struct_pb2.Struct()
    message.update(payload)
    return message


def build_mock_response(service_name: str, rpc_method: str, request_payload: dict[str, Any]) -> dict[str, Any]:
    order_id = str(request_payload.get("order_id", "ord-mock"))
    worker_id = str(request_payload.get("worker_id", "worker-mock"))

    if rpc_method in {"StartService", "CompleteService", "GetServiceRecord"}:
        status = "IN_SERVICE" if rpc_method == "StartService" else "COMPLETE"
        return {
            "record": {
                "order_id": order_id,
                "worker_id": worker_id,
                "status": status,
                "started_at": str(request_payload.get("started_at", "")),
                "completed_at": str(request_payload.get("completed_at", "")),
                "actual_duration_minutes": int(request_payload.get("actual_duration_minutes", 0) or 0),
                "completion_note": str(request_payload.get("completion_note", "")),
                "photos": [],
            }
        }

    if rpc_method == "AddServicePhoto":
        return {
            "photo": {
                "photo_id": "photo-mock",
                "order_id": order_id,
                "photo_url": str(request_payload.get("photo_url", "")),
                "photo_type": str(request_payload.get("photo_type", "")),
                "remark": str(request_payload.get("remark", "")),
                "uploaded_by": worker_id,
                "uploaded_at": "",
            }
        }

    if rpc_method == "CreatePayment":
        return {
            "payment": {
                "payment_id": "pay-mock",
                "order_id": order_id,
                "amount": int(request_payload.get("amount", 0) or 0),
                "currency": str(request_payload.get("currency", "CNY")),
                "payment_method": str(request_payload.get("payment_method", "")),
                "payment_status": "PAID",
                "paid_at": str(request_payload.get("paid_at", "")),
                "confirmed_by": "",
                "remark": str(request_payload.get("remark", "")),
                "created_at": "",
            }
        }

    if rpc_method == "ListOrderPayments":
        return {"payments": []}

    return {
        "service": service_name,
        "rpc_method": rpc_method,
        "request": request_payload,
    }


class GenericEchoHandler(grpc.aio.GenericRpcHandler):
    def __init__(self, service_name: str, service_full_name: str):
        self._service_name = service_name
        self._service_full_name = service_full_name

    def service(self, handler_call_details: grpc.HandlerCallDetails):
        method_path = handler_call_details.method
        prefix = f"/{self._service_full_name}/"
        if not method_path.startswith(prefix):
            return None

        rpc_method = method_path.removeprefix(prefix)

        async def unary_unary(request: struct_pb2.Struct, context: grpc.aio.ServicerContext):
            incoming_metadata = {item.key: item.value for item in context.invocation_metadata()}
            request_payload = struct_to_dict(request)
            response_payload = build_mock_response(self._service_name, rpc_method, request_payload)
            response_payload["received_metadata"] = {
                "x-user-id": incoming_metadata.get("x-user-id", ""),
                "x-user-email": incoming_metadata.get("x-user-email", ""),
                "x-user-role": incoming_metadata.get("x-user-role", ""),
                "x-request-id": incoming_metadata.get("x-request-id", ""),
                "x-auth-source": incoming_metadata.get("x-auth-source", ""),
            }
            return dict_to_struct(response_payload)

        return grpc.unary_unary_rpc_method_handler(
            unary_unary,
            request_deserializer=struct_pb2.Struct.FromString,
            response_serializer=struct_pb2.Struct.SerializeToString,
        )


async def main() -> None:
    service_name = os.getenv("SERVICE_NAME", "mock-service")
    service_full_name = os.getenv("SERVICE_FULL_NAME", "hsp.mock.v1.MockService")
    grpc_port = int(os.getenv("GRPC_PORT", "50051"))

    server = grpc.aio.server()
    server.add_generic_rpc_handlers([GenericEchoHandler(service_name, service_full_name)])
    server.add_insecure_port(f"[::]:{grpc_port}")

    await server.start()
    print(f"{service_name} listening on {grpc_port} for {service_full_name}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())

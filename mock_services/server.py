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
            response_payload = {
                "service": self._service_name,
                "rpc_method": rpc_method,
                "request": struct_to_dict(request),
                "received_metadata": {
                    "x-user-id": incoming_metadata.get("x-user-id", ""),
                    "x-user-email": incoming_metadata.get("x-user-email", ""),
                    "x-user-role": incoming_metadata.get("x-user-role", ""),
                    "x-request-id": incoming_metadata.get("x-request-id", ""),
                    "x-auth-source": incoming_metadata.get("x-auth-source", ""),
                },
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

from __future__ import annotations

import time

import grpc
import jwt


class FakeRpcError(grpc.RpcError):
    def __init__(self, status: grpc.StatusCode, details: str):
        super().__init__()
        self._status = status
        self._details = details

    def code(self):
        return self._status

    def details(self):
        return self._details


def make_token(role: str = "OWNER", sub: str = "u-910", email: str = "owner@example.com") -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "iss": "hsp-user-service",
        "aud": "hsp-api",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, "replace_me", algorithm="HS256")


def test_worker_can_start_service_and_forward_metadata(client):
    captured: dict[str, object] = {}

    async def fake_call(payload, metadata):
        captured["payload"] = payload
        captured["metadata"] = dict(metadata)
        return {
            "record": {
                "order_id": payload["order_id"],
                "worker_id": payload["worker_id"],
                "status": "IN_SERVICE",
                "started_at": payload["started_at"],
                "photos": [],
            }
        }

    client.app.state.grpc_clients.service_execution_start_service = fake_call

    token = make_token(role="WORKER", sub="worker-1001", email="worker@example.com")
    resp = client.post(
        "/api/service-execution/v1/orders/ord-1001/start",
        json={"worker_id": "worker-1001", "started_at": "2026-04-08T10:05:00+08:00"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["record"]["status"] == "IN_SERVICE"
    assert captured["payload"]["order_id"] == "ord-1001"
    metadata = captured["metadata"]
    assert metadata["x-user-id"] == "worker-1001"
    assert metadata["x-user-role"] == "WORKER"
    assert metadata["x-auth-source"] == "gateway"


def test_worker_can_complete_service(client):
    async def fake_call(payload, metadata):
        return {
            "record": {
                "order_id": payload["order_id"],
                "worker_id": payload["worker_id"],
                "status": "COMPLETE",
                "actual_duration_minutes": payload["actual_duration_minutes"],
                "photos": [],
            }
        }

    client.app.state.grpc_clients.service_execution_complete_service = fake_call

    token = make_token(role="WORKER")
    resp = client.post(
        "/api/service-execution/v1/orders/ord-1001/complete",
        json={"worker_id": "worker-1001", "actual_duration_minutes": 125},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["record"]["status"] == "COMPLETE"


def test_add_service_photo_and_get_record(client):
    async def fake_add(payload, metadata):
        return {
            "photo": {
                "photo_id": "photo-1",
                "order_id": payload["order_id"],
                "photo_url": payload["photo_url"],
                "photo_type": payload["photo_type"],
                "remark": payload.get("remark"),
            }
        }

    async def fake_get(payload, metadata):
        return {
            "record": {
                "order_id": payload["order_id"],
                "worker_id": "worker-1001",
                "status": "COMPLETE",
                "photos": [],
            }
        }

    client.app.state.grpc_clients.service_execution_add_photo = fake_add
    client.app.state.grpc_clients.service_execution_get_record = fake_get

    token = make_token(role="WORKER")
    add_resp = client.post(
        "/api/service-execution/v1/orders/ord-1001/photos",
        json={"photo_url": "https://example.com/a.jpg", "photo_type": "AFTER", "remark": "完成照片"},
        headers={"Authorization": f"Bearer {token}"},
    )
    get_resp = client.get(
        "/api/service-execution/v1/orders/ord-1001/record",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert add_resp.status_code == 200
    assert add_resp.json()["photo"]["photo_type"] == "AFTER"
    assert get_resp.status_code == 200
    assert get_resp.json()["record"]["order_id"] == "ord-1001"


def test_customer_service_can_create_payment_and_close_order(client):
    captured: dict[str, object] = {}

    async def fake_payment(payload, metadata):
        captured["payment_payload"] = payload
        captured["payment_metadata"] = dict(metadata)
        return {
            "payment": {
                "payment_id": "pay-1001",
                "order_id": payload["order_id"],
                "amount": payload["amount"],
                "currency": payload["currency"],
                "payment_method": payload["payment_method"],
                "payment_status": "PAID",
            }
        }

    async def fake_close(payload, metadata):
        captured["close_payload"] = payload
        return {
            "order": {
                "order_id": payload["order_id"],
                "status": "ORDER_STATUS_PAID",
                "assigned_worker_id": payload.get("assigned_worker_id"),
            }
        }

    client.app.state.grpc_clients.finance_create_payment = fake_payment
    client.app.state.grpc_clients.order_update_status = fake_close

    token = make_token(role="CUSTOMER_SERVICE", sub="cs-1001", email="cs@example.com")
    payment_resp = client.post(
        "/api/finance/v1/orders/ord-1001/payments",
        json={"amount": 26800, "currency": "CNY", "payment_method": "WECHAT"},
        headers={"Authorization": f"Bearer {token}"},
    )
    close_resp = client.post(
        "/api/orders/v1/orders/ord-1001/close",
        json={"payment_id": "pay-1001", "close_reason": "用户已付款"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert payment_resp.status_code == 200
    assert close_resp.status_code == 200
    assert captured["payment_payload"]["order_id"] == "ord-1001"
    assert captured["payment_metadata"]["x-user-role"] == "CUSTOMER_SERVICE"
    assert captured["close_payload"]["target_status"] == "PAID"


def test_worker_cannot_create_payment_or_close_order(client):
    token = make_token(role="WORKER")

    payment_resp = client.post(
        "/api/finance/v1/orders/ord-1001/payments",
        json={"amount": 26800, "currency": "CNY", "payment_method": "WECHAT"},
        headers={"Authorization": f"Bearer {token}"},
    )
    close_resp = client.post(
        "/api/orders/v1/orders/ord-1001/close",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert payment_resp.status_code == 403
    assert close_resp.status_code == 403


def test_new_endpoints_are_in_openapi(client):
    resp = client.get("/openapi.json")

    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/service-execution/v1/orders/{order_id}/start" in paths
    assert "/api/service-execution/v1/orders/{order_id}/complete" in paths
    assert "/api/service-execution/v1/orders/{order_id}/photos" in paths
    assert "/api/service-execution/v1/orders/{order_id}/record" in paths
    assert "/api/finance/v1/orders/{order_id}/payments" in paths
    assert "/api/orders/v1/orders/{order_id}/close" in paths


def test_worker_schedule_unimplemented_falls_back_to_mock_response(client):
    async def fake_register(payload, metadata):
        raise FakeRpcError(grpc.StatusCode.UNIMPLEMENTED, "not implemented")

    client.app.state.grpc_clients.worker_schedule_register_worker = fake_register

    token = make_token(role="CUSTOMER_SERVICE")
    resp = client.post(
        "/api/worker-schedule/v1/workers/register",
        json={"worker_id": "worker-1001", "worker_name": "王师傅"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["worker"]["id"] == "worker-1001"


def test_service_execution_not_found_falls_back_and_can_be_verified(client):
    async def fake_start(payload, metadata):
        raise FakeRpcError(grpc.StatusCode.NOT_FOUND, "service record missing")

    client.app.state.grpc_clients.service_execution_start_service = fake_start

    token = make_token(role="WORKER", sub="worker-1001")
    start_resp = client.post(
        "/api/service-execution/v1/orders/ord-1001/start",
        json={"worker_id": "worker-1001"},
        headers={"Authorization": f"Bearer {token}"},
    )
    record_resp = client.get(
        "/api/service-execution/v1/orders/ord-1001/record",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert start_resp.status_code == 200
    assert start_resp.json()["record"]["status"] == "IN_SERVICE"
    assert record_resp.status_code == 200
    assert record_resp.json()["record"]["order_id"] == "ord-1001"


def test_service_execution_unavailable_falls_back_for_core_flow(client):
    async def fake_start(payload, metadata):
        raise FakeRpcError(grpc.StatusCode.UNAVAILABLE, "service execution unavailable")

    async def fake_complete(payload, metadata):
        raise FakeRpcError(grpc.StatusCode.UNAVAILABLE, "service execution unavailable")

    client.app.state.grpc_clients.service_execution_start_service = fake_start
    client.app.state.grpc_clients.service_execution_complete_service = fake_complete

    token = make_token(role="WORKER", sub="worker-1001")
    start_resp = client.post(
        "/api/service-execution/v1/orders/ord-1001/start",
        json={"worker_id": "worker-1001", "started_at": "2026-04-08T10:05:00+08:00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    complete_resp = client.post(
        "/api/service-execution/v1/orders/ord-1001/complete",
        json={"worker_id": "worker-1001", "actual_duration_minutes": 125},
        headers={"Authorization": f"Bearer {token}"},
    )
    record_resp = client.get(
        "/api/service-execution/v1/orders/ord-1001/record",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert start_resp.status_code == 200
    assert complete_resp.status_code == 200
    assert complete_resp.json()["record"]["status"] == "COMPLETE"
    assert record_resp.status_code == 200
    assert record_resp.json()["record"]["status"] == "COMPLETE"


def test_payment_not_found_falls_back_and_can_be_listed(client):
    async def fake_payment(payload, metadata):
        raise FakeRpcError(grpc.StatusCode.NOT_FOUND, "payment service has no record")

    client.app.state.grpc_clients.finance_create_payment = fake_payment

    token = make_token(role="CUSTOMER_SERVICE", sub="cs-1001")
    payment_resp = client.post(
        "/api/finance/v1/orders/ord-1001/payments",
        json={"amount": 26800, "currency": "CNY", "payment_method": "WECHAT"},
        headers={"Authorization": f"Bearer {token}"},
    )
    list_resp = client.get(
        "/api/finance/v1/orders/ord-1001/payments",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert payment_resp.status_code == 200
    assert payment_resp.json()["payment"]["payment_status"] == "PAID"
    assert list_resp.status_code == 200
    assert list_resp.json()["payments"][0]["payment_id"] == "pay-ord-1001"

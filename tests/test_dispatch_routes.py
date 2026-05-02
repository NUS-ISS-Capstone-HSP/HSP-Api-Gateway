from __future__ import annotations

import time

import jwt


def make_token(role: str = "OWNER", sub: str = "u-900", email: str = "owner@example.com") -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "iss": "hsp-user-service",
        "aud": "hsp-api",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, "replace_me", algorithm="HS256")


def test_dispatch_list_available_workers_should_forward_query_and_metadata(client):
    captured: dict[str, object] = {}

    async def fake_call(payload, metadata):
        captured["payload"] = payload
        captured["metadata"] = dict(metadata)
        return {"workers": []}

    client.app.state.grpc_clients.dispatch_list_available_workers = fake_call

    token = make_token()
    resp = client.get(
        "/api/dispatch/v1/workers/available?service_type=CLEANING&region=sh-pd&at_time=2026-04-07T12:00:00%2B08:00&limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["workers"] == []

    payload = captured["payload"]
    metadata = captured["metadata"]
    assert payload["service_type"] == "CLEANING"
    assert payload["region"] == "sh-pd"
    assert payload["limit"] == 5
    assert metadata["x-user-id"] == "u-900"
    assert metadata["x-user-role"] == "OWNER"
    assert metadata["x-auth-source"] == "gateway"


def test_dispatch_manual_assign_without_token_returns_401(client):
    resp = client.post(
        "/api/dispatch/v1/assignments/manual",
        json={"order_id": "ord-1", "worker_id": "worker-1"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"

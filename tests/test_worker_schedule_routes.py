from __future__ import annotations

import time

import jwt


def make_token(role: str = "OWNER", sub: str = "u-901", email: str = "owner@example.com") -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "iss": "hsp-user-service",
        "aud": "hsp-api",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, "replace_me", algorithm="HS256")


def test_worker_schedule_list_workers_should_forward_metadata(client):
    captured: dict[str, object] = {}

    async def fake_call(payload, metadata):
        captured["payload"] = payload
        captured["metadata"] = dict(metadata)
        return {"workers": []}

    client.app.state.grpc_clients.worker_schedule_list_workers = fake_call

    token = make_token()
    resp = client.get(
        "/api/worker-schedule/v1/workers",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["workers"] == []
    metadata = captured["metadata"]
    assert metadata["x-user-id"] == "u-901"
    assert metadata["x-user-role"] == "OWNER"
    assert metadata["x-auth-source"] == "gateway"


def test_worker_schedule_register_without_token_returns_401(client):
    resp = client.post(
        "/api/worker-schedule/v1/workers/register",
        json={"worker_id": "worker-1", "worker_name": "A"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"

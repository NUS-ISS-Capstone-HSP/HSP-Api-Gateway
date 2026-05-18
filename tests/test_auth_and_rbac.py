from __future__ import annotations

import time

import jwt


def make_token(role: str, sub: str = "u-100", email: str = "u100@example.com") -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "iss": "hsp-user-service",
        "aud": "hsp-api",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, "replace_me", algorithm="HS256")


def test_protected_path_without_token_returns_401(client):
    resp = client.get("/api/users/v1/profile")
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "AUTH_REQUIRED"
    assert "request_id" in data


def test_invalid_token_returns_401(client):
    resp = client.get(
        "/api/users/v1/profile",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "TOKEN_INVALID"


def test_missing_required_claim_returns_401(client):
    payload = {
        "sub": "u-100",
        "email": "u100@example.com",
        "role": "OWNER",
        "iss": "hsp-user-service",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, "replace_me", algorithm="HS256")

    resp = client.get(
        "/api/users/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "TOKEN_INVALID"


def test_worker_cannot_access_admin(client):
    token = make_token(role="WORKER")

    resp = client.get(
        "/api/users/v1/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403
    data = resp.json()
    assert data["code"] == "FORBIDDEN"


def test_customer_service_can_dispatch_and_forward(client):
    captured: dict[str, object] = {}

    async def fake_dispatch(payload, metadata):
        captured["payload"] = payload
        captured["metadata"] = dict(metadata)
        return {"message": "dispatched"}

    client.app.state.grpc_clients.user_dispatch = fake_dispatch

    token = make_token(role="CUSTOMER_SERVICE", sub="u-200", email="cs@example.com")
    resp = client.post(
        "/api/users/v1/orders/dispatch",
        json={"order_id": "ord-001"},
        headers={
            "Authorization": f"Bearer {token}",
            "x-user-id": "attacker",
            "x-user-role": "OWNER",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["message"] == "dispatched"
    metadata = captured["metadata"]
    assert metadata["x-user-id"] == "u-200"
    assert metadata["x-user-email"] == "cs@example.com"
    assert metadata["x-user-role"] == "CUSTOMER_SERVICE"
    assert metadata["x-auth-source"] == "gateway"

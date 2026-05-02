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


def make_token(role: str, sub: str = "u-300", email: str = "u300@example.com") -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "iss": "hsp-user-service",
        "aud": "hsp-api",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, "replace_me", algorithm="HS256")


def test_whitelist_login_without_token_should_pass(client):
    captured: dict[str, object] = {}

    async def fake_login(payload, metadata):
        captured["payload"] = payload
        captured["metadata"] = dict(metadata)
        return {"access_token": "mock-token", "token_type": "bearer", "expires_in": 3600}

    client.app.state.grpc_clients.user_login = fake_login

    resp = client.post("/api/users/v1/auth/login", json={"email": "a@b.com", "password": "x"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == "mock-token"
    metadata = captured["metadata"]
    assert metadata["x-auth-source"] == "gateway"


def test_swagger_docs_without_token_should_pass(client):
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "Swagger UI" in resp.text


def test_grpc_not_found_maps_to_http_404(client):
    async def fake_get_invoice(payload, metadata):
        raise FakeRpcError(grpc.StatusCode.NOT_FOUND, "invoice missing")

    client.app.state.grpc_clients.finance_get_invoice = fake_get_invoice

    token = make_token(role="OWNER")
    resp = client.get(
        "/api/finance/v1/invoices/inv-404",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "GRPC_NOT_FOUND"
    assert body["message"] == "invoice missing"

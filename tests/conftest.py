from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def set_env() -> Generator[None, None, None]:
    os.environ["GATEWAY_HOST"] = "0.0.0.0"
    os.environ["GATEWAY_PORT"] = "8081"
    os.environ["JWT_SECRET"] = "replace_me"
    os.environ["JWT_ISSUER"] = "hsp-user-service"
    os.environ["JWT_AUDIENCE"] = "hsp-api"
    os.environ["USER_GRPC_TARGET"] = "user-service:50051"
    os.environ["ORDER_GRPC_TARGET"] = "order-service:50051"
    os.environ["DISPATCH_GRPC_TARGET"] = "dispatch-service:50051"
    os.environ["WORKER_SCHEDULE_GRPC_TARGET"] = "worker-schedule-service:50051"
    os.environ["FINANCE_GRPC_TARGET"] = "finance-service:50051"
    os.environ["GRPC_TIMEOUT_MS"] = "3000"
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

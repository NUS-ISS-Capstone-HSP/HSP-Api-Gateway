from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    gateway_host: str = Field(default="0.0.0.0", alias="GATEWAY_HOST")
    gateway_port: int = Field(default=8081, alias="GATEWAY_PORT")

    jwt_secret: str = Field(default="replace_me", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="hsp-user-service", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="hsp-api", alias="JWT_AUDIENCE")

    user_grpc_target: str = Field(default="user-service:50051", alias="USER_GRPC_TARGET")
    order_grpc_target: str = Field(default="order-service:50051", alias="ORDER_GRPC_TARGET")
    dispatch_grpc_target: str = Field(default="dispatch-service:50051", alias="DISPATCH_GRPC_TARGET")
    worker_schedule_grpc_target: str = Field(
        default="worker-schedule-service:50051",
        alias="WORKER_SCHEDULE_GRPC_TARGET",
    )
    finance_grpc_target: str = Field(default="finance-service:50051", alias="FINANCE_GRPC_TARGET")

    grpc_timeout_ms: int = Field(default=3000, alias="GRPC_TIMEOUT_MS")

    @property
    def grpc_timeout_seconds(self) -> float:
        return self.grpc_timeout_ms / 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()

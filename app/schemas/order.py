from __future__ import annotations

from pydantic import BaseModel, Field


class OrderModel(BaseModel):
    order_id: str | None = None
    customer_name: str | None = None
    phone: str | None = None
    service_address: str | None = None
    service_type: str | None = None
    appointment_time: str | None = None
    estimated_duration_minutes: int | None = None
    status: str | None = None
    assigned_worker_id: str | None = None
    status_updated_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CreateOrderRequestModel(BaseModel):
    customer_name: str = Field(..., examples=["张三"])
    phone: str = Field(..., examples=["13800000000"])
    service_address: str = Field(..., examples=["上海市浦东新区XX路100号"])
    service_type: str = Field(
        ...,
        description="支持 CLEANING/REPAIR/INSTALL/OTHER，或 proto 枚举名 SERVICE_TYPE_*",
        examples=["CLEANING"],
    )
    appointment_time: str = Field(..., examples=["2026-04-08T10:00:00+08:00"])
    estimated_duration_minutes: int = Field(..., ge=1, examples=[120])


class CreateOrderResponseModel(BaseModel):
    order: OrderModel


class GetOrderResponseModel(BaseModel):
    order: OrderModel


class ListOrdersResponseModel(BaseModel):
    items: list[OrderModel] = Field(default_factory=list)
    page: int | None = None
    page_size: int | None = None
    total: int | None = None


class UpdateOrderStatusBodyModel(BaseModel):
    target_status: str = Field(
        ...,
        description="支持 CREATED/PENDING/ACCEPT/COMPLETE/PAID，或 proto 枚举名 ORDER_STATUS_*",
        examples=["ACCEPT"],
    )
    assigned_worker_id: str | None = Field(default=None, examples=["worker-1001"])


class UpdateOrderStatusResponseModel(BaseModel):
    order: OrderModel

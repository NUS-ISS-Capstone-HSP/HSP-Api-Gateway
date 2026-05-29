from __future__ import annotations

from pydantic import BaseModel, Field


class PaymentRecordModel(BaseModel):
    payment_id: str | None = None
    order_id: str | None = None
    amount: int | None = None
    currency: str | None = None
    payment_method: str | None = None
    payment_status: str | None = None
    paid_at: str | None = None
    confirmed_by: str | None = None
    remark: str | None = None
    created_at: str | None = None


class CreatePaymentRequestModel(BaseModel):
    amount: int = Field(..., ge=1, description="支付金额，单位：分", examples=[26800])
    currency: str = Field(default="CNY", examples=["CNY"])
    payment_method: str = Field(
        ...,
        description="建议使用 WECHAT/CASH/BANK_TRANSFER/OTHER",
        examples=["WECHAT"],
    )
    paid_at: str | None = Field(default=None, examples=["2026-04-08T12:30:00+08:00"])
    remark: str | None = Field(default=None, examples=["客服已核对微信收款截图"])


class CreatePaymentResponseModel(BaseModel):
    payment: PaymentRecordModel


class ListOrderPaymentsResponseModel(BaseModel):
    payments: list[PaymentRecordModel] = Field(default_factory=list)

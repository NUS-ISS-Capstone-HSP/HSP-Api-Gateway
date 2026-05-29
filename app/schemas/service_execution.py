from __future__ import annotations

from pydantic import BaseModel, Field


class ServicePhotoModel(BaseModel):
    photo_id: str | None = None
    order_id: str | None = None
    photo_url: str | None = None
    photo_type: str | None = None
    remark: str | None = None
    uploaded_by: str | None = None
    uploaded_at: str | None = None


class ServiceRecordModel(BaseModel):
    order_id: str | None = None
    worker_id: str | None = None
    status: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    actual_duration_minutes: int | None = None
    completion_note: str | None = None
    photos: list[ServicePhotoModel] = Field(default_factory=list)


class StartServiceRequestModel(BaseModel):
    worker_id: str | None = Field(default=None, examples=["worker-1001"])
    started_at: str | None = Field(default=None, examples=["2026-04-08T10:05:00+08:00"])
    remark: str | None = Field(default=None, examples=["已到达客户现场"])


class StartServiceResponseModel(BaseModel):
    record: ServiceRecordModel


class CompleteServiceRequestModel(BaseModel):
    worker_id: str | None = Field(default=None, examples=["worker-1001"])
    completed_at: str | None = Field(default=None, examples=["2026-04-08T12:10:00+08:00"])
    actual_duration_minutes: int | None = Field(default=None, ge=1, examples=[125])
    completion_note: str | None = Field(default=None, examples=["深度保洁已完成，客户现场确认"])


class CompleteServiceResponseModel(BaseModel):
    record: ServiceRecordModel


class AddServicePhotoRequestModel(BaseModel):
    photo_url: str = Field(..., examples=["https://example.com/service-photos/ord-1001-before.jpg"])
    photo_type: str = Field(
        ...,
        description="建议使用 BEFORE/AFTER/RECEIPT/OTHER",
        examples=["AFTER"],
    )
    remark: str | None = Field(default=None, examples=["客厅清洁完成照片"])


class AddServicePhotoResponseModel(BaseModel):
    photo: ServicePhotoModel


class GetServiceRecordResponseModel(BaseModel):
    record: ServiceRecordModel

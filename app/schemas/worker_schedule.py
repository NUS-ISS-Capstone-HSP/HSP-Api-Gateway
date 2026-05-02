from __future__ import annotations

from pydantic import BaseModel, Field


class WorkerRecordModel(BaseModel):
    id: str | None = None
    name: str | None = None
    status: str | None = None
    updated_at: str | None = None


class RegisterWorkerRequestModel(BaseModel):
    worker_id: str = Field(..., examples=["worker-1001"])
    worker_name: str = Field(..., examples=["王师傅"])


class RegisterWorkerResponseModel(BaseModel):
    worker: WorkerRecordModel


class ListWorkersResponseModel(BaseModel):
    workers: list[WorkerRecordModel] = Field(default_factory=list)


class UpdateWorkerStatusBodyModel(BaseModel):
    status: str = Field(
        ...,
        description="支持 AVAILABLE/ASSIGNED/IN_SERVICE 或 proto 枚举名 WORKER_STATUS_*",
        examples=["AVAILABLE"],
    )


class UpdateWorkerStatusResponseModel(BaseModel):
    worker: WorkerRecordModel


class SyncOrderEventRequestModel(BaseModel):
    order_id: str = Field(..., examples=["ord-1001"])
    worker_id: str = Field(..., examples=["worker-1001"])
    worker_name: str = Field(..., examples=["王师傅"])
    event_type: str = Field(
        ...,
        description="支持 ASSIGNED/SERVICE_STARTED/COMPLETED/CANCELED 或 proto 枚举名 ORDER_EVENT_TYPE_*",
        examples=["ASSIGNED"],
    )
    start_time: str = Field(default="", examples=["2026-04-07T10:00:00+08:00"])
    end_time: str = Field(default="", examples=["2026-04-07T11:00:00+08:00"])
    title: str = Field(default="", examples=["空调安装"])


class SyncOrderEventResponseModel(BaseModel):
    worker: WorkerRecordModel


class ScheduleTaskRecordModel(BaseModel):
    order_id: str | None = None
    worker_id: str | None = None
    worker_name: str | None = None
    title: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    status: str | None = None
    updated_at: str | None = None
    has_conflict: bool | None = None


class ListDailyScheduleResponseModel(BaseModel):
    tasks: list[ScheduleTaskRecordModel] = Field(default_factory=list)


class GetOrderDetailResponseModel(BaseModel):
    task: ScheduleTaskRecordModel | None = None

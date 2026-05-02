from __future__ import annotations

from pydantic import BaseModel, Field


class WorkerModel(BaseModel):
    worker_id: str | None = None
    name: str | None = None
    skills: list[str] = Field(default_factory=list)
    status: str | None = None


class DispatchRecordModel(BaseModel):
    dispatch_id: str | None = None
    order_id: str | None = None
    attempt_no: int | None = None
    worker_id: str | None = None
    operator_id: str | None = None
    status: str | None = None
    assigned_at: str | None = None
    responded_at: str | None = None
    reject_reason: str | None = None


class ListAvailableWorkersResponseModel(BaseModel):
    workers: list[WorkerModel] = Field(default_factory=list)


class ManualAssignOrderRequestModel(BaseModel):
    order_id: str = Field(..., examples=["ord-1001"])
    worker_id: str = Field(..., examples=["worker-1001"])


class ManualAssignOrderResponseModel(BaseModel):
    dispatch: DispatchRecordModel


class ListWorkerPendingDispatchesResponseModel(BaseModel):
    dispatches: list[DispatchRecordModel] = Field(default_factory=list)


class ConfirmWorkerResponseRequestModel(BaseModel):
    response: str = Field(
        ...,
        description="支持 ACCEPT/REJECT 或 proto 枚举名 WORKER_RESPONSE_TYPE_*",
        examples=["ACCEPT"],
    )
    reject_reason: str | None = Field(default=None, examples=["当前时间冲突"])


class ConfirmWorkerResponseResponseModel(BaseModel):
    dispatch: DispatchRecordModel


class GetOrderDispatchHistoryResponseModel(BaseModel):
    dispatches: list[DispatchRecordModel] = Field(default_factory=list)

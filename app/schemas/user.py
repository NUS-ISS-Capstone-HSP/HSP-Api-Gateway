from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequestModel(BaseModel):
    email: str = Field(..., examples=["owner@example.com"])
    password: str = Field(..., examples=["StrongPassword!123"])
    role: str = Field(
        ...,
        description="支持 WORKER/CUSTOMER_SERVICE/OWNER，或 proto 枚举名 USER_ROLE_*",
        examples=["OWNER"],
    )
    worker_display_name: str = Field(default="", examples=["张三"])


class LoginRequestModel(BaseModel):
    email: str = Field(..., examples=["owner@example.com"])
    password: str = Field(..., examples=["StrongPassword!123"])


class DispatchOrderRequestModel(BaseModel):
    # 对应 proto 的空请求体，当前无需字段
    pass


class WorkerProfileModel(BaseModel):
    id: int
    user_id: int
    worker_no: str
    display_name: str
    employment_status: str
    created_at: str
    updated_at: str


class UserModel(BaseModel):
    id: int
    email: str
    role: str
    status: str
    created_at: str
    updated_at: str
    last_login_at: str | None = None
    worker_profile: WorkerProfileModel | None = None


class RegisterResponseModel(BaseModel):
    user: UserModel


class LoginResponseModel(BaseModel):
    access_token: str
    token_type: str | None = None
    expires_in: int | None = None
    user: UserModel | None = None


class GetMeResponseModel(BaseModel):
    user: UserModel


class MessageResponseModel(BaseModel):
    message: str

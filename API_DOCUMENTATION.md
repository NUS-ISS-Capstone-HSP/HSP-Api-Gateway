# HSP API Gateway API Documentation

Base URL: `http://127.0.0.1:8081`

Authentication: all endpoints require `Authorization: Bearer <JWT>` except `GET /healthz`, `POST /api/users/v1/auth/register`, and `POST /api/users/v1/auth/login`.

Roles:
- `WORKER`: worker app actions, including pending dispatches and service execution.
- `CUSTOMER_SERVICE`: order creation, dispatch, payment confirmation, and close order.
- `OWNER`: admin-level access, payment confirmation, and close order.

Error format:

```json
{
  "code": "FORBIDDEN",
  "message": "Role cannot close orders",
  "request_id": "..."
}
```

## Core Integration Flow

1. Customer service logs in or uses a `CUSTOMER_SERVICE` JWT.
2. Create an order with `POST /api/orders/v1/orders`.
3. Query available workers with `GET /api/dispatch/v1/workers/available`.
4. Assign a worker with `POST /api/dispatch/v1/assignments/manual`.
5. Worker logs in or uses a `WORKER` JWT.
6. Worker lists pending dispatches with `GET /api/dispatch/v1/worker/pending-dispatches`.
7. Worker confirms the dispatch with `POST /api/dispatch/v1/dispatches/{dispatch_id}/confirm`.
8. Worker starts service with `POST /api/service-execution/v1/orders/{order_id}/start`.
9. Worker completes service with `POST /api/service-execution/v1/orders/{order_id}/complete`.
10. Customer service confirms payment with `POST /api/finance/v1/orders/{order_id}/payments`.
11. Customer service closes the order with `POST /api/orders/v1/orders/{order_id}/close`.
12. Verify the result with order detail, dispatch history, service record, and payment list APIs.

Order lifecycle:

```text
CREATED -> PENDING -> ACCEPT -> IN_SERVICE -> COMPLETE -> PAID
```

`ACCEPT` means the worker accepted the dispatch. `PAID` means payment has been confirmed and the order is closed.

## Health

### GET `/healthz`

Public health check.

Response:

```json
{
  "status": "ok"
}
```

## User APIs

### POST `/api/users/v1/auth/register`

Public registration API.

Request:

```json
{
  "email": "owner@example.com",
  "password": "StrongPassword!123",
  "role": "OWNER",
  "worker_display_name": "王师傅"
}
```

Response:

```json
{
  "user": {
    "id": 1,
    "email": "owner@example.com",
    "role": "USER_ROLE_OWNER",
    "status": "USER_STATUS_ACTIVE",
    "created_at": "2026-04-08T09:00:00+08:00",
    "updated_at": "2026-04-08T09:00:00+08:00",
    "last_login_at": null,
    "worker_profile": null
  }
}
```

### POST `/api/users/v1/auth/login`

Public login API.

Request:

```json
{
  "email": "owner@example.com",
  "password": "StrongPassword!123"
}
```

Response:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "email": "owner@example.com",
    "role": "USER_ROLE_OWNER",
    "status": "USER_STATUS_ACTIVE",
    "created_at": "2026-04-08T09:00:00+08:00",
    "updated_at": "2026-04-08T09:00:00+08:00",
    "last_login_at": "2026-04-08T09:10:00+08:00",
    "worker_profile": null
  }
}
```

### GET `/api/users/v1/profile`

Returns the current authenticated user profile.

### GET `/api/users/v1/admin/ping`

Admin ping endpoint. `WORKER` is forbidden.

### POST `/api/users/v1/orders/dispatch`

Legacy dispatch permission check endpoint. Prefer `POST /api/dispatch/v1/assignments/manual` for real dispatch tests.

## Order APIs

### POST `/api/orders/v1/orders`

Creates a structured service order.

Request:

```json
{
  "customer_name": "张三",
  "phone": "13800000000",
  "service_address": "南通市崇川区人民中路100号",
  "service_type": "CLEANING",
  "appointment_time": "2026-04-08T10:00:00+08:00",
  "estimated_duration_minutes": 120
}
```

Response:

```json
{
  "order": {
    "order_id": "ord-1001",
    "customer_name": "张三",
    "phone": "13800000000",
    "service_address": "南通市崇川区人民中路100号",
    "service_type": "SERVICE_TYPE_CLEANING",
    "appointment_time": "2026-04-08T10:00:00+08:00",
    "estimated_duration_minutes": 120,
    "status": "ORDER_STATUS_CREATED",
    "assigned_worker_id": "",
    "status_updated_at": "2026-04-08T09:00:00+08:00",
    "created_at": "2026-04-08T09:00:00+08:00",
    "updated_at": "2026-04-08T09:00:00+08:00"
  }
}
```

### GET `/api/orders/v1/orders`

Lists orders.

Query parameters:
- `customer_name`
- `service_type`: `CLEANING`, `REPAIR`, `INSTALL`, `OTHER`, or proto enum name.
- `status`: `CREATED`, `PENDING`, `ACCEPT`, `IN_SERVICE`, `COMPLETE`, `PAID`, or proto enum name.
- `page`: default `1`.
- `page_size`: default `20`, max `200`.

### GET `/api/orders/v1/orders/{order_id}`

Returns one order.

### PATCH `/api/orders/v1/orders/{order_id}/status`

Generic status transition endpoint.

Request:

```json
{
  "target_status": "ACCEPT",
  "assigned_worker_id": "worker-1001"
}
```

### POST `/api/orders/v1/orders/{order_id}/close`

Semantic close-order endpoint. The gateway always forwards `target_status=PAID`; callers do not choose the final status.

Allowed roles: `CUSTOMER_SERVICE`, `OWNER`.

Request:

```json
{
  "payment_id": "pay-1001",
  "close_reason": "用户已付款，客服确认关单"
}
```

Response:

```json
{
  "order": {
    "order_id": "ord-1001",
    "status": "ORDER_STATUS_PAID",
    "assigned_worker_id": "worker-1001"
  }
}
```

## Dispatch APIs

### GET `/api/dispatch/v1/workers/available`

Lists available workers for dispatch.

Query parameters:
- `service_type`: optional.
- `region`: optional.
- `at_time`: optional ISO-8601 time.
- `limit`: default `20`, max `200`.

Response:

```json
{
  "workers": [
    {
      "worker_id": "worker-1001",
      "name": "王师傅",
      "skills": ["CLEANING"],
      "status": "AVAILABLE"
    }
  ]
}
```

### POST `/api/dispatch/v1/assignments/manual`

Manually assigns an order to a worker.

Request:

```json
{
  "order_id": "ord-1001",
  "worker_id": "worker-1001"
}
```

Response:

```json
{
  "dispatch": {
    "dispatch_id": "dispatch-1001",
    "order_id": "ord-1001",
    "attempt_no": 1,
    "worker_id": "worker-1001",
    "operator_id": "cs-1001",
    "status": "PENDING_WORKER_CONFIRM",
    "assigned_at": "2026-04-08T09:05:00+08:00",
    "responded_at": null,
    "reject_reason": null
  }
}
```

### GET `/api/dispatch/v1/worker/pending-dispatches`

Lists dispatches pending confirmation for the current worker.

### POST `/api/dispatch/v1/dispatches/{dispatch_id}/confirm`

Worker accepts or rejects a dispatch.

Request:

```json
{
  "response": "ACCEPT",
  "reject_reason": null
}
```

### GET `/api/dispatch/v1/orders/{order_id}/history`

Returns dispatch attempts for one order.

## Worker Schedule APIs

### POST `/api/worker-schedule/v1/workers/register`

Registers a worker in the schedule service.

Request:

```json
{
  "worker_id": "worker-1001",
  "worker_name": "王师傅"
}
```

### GET `/api/worker-schedule/v1/workers`

Lists workers and schedule status.

### PATCH `/api/worker-schedule/v1/workers/{worker_id}/status`

Updates schedule status.

Request:

```json
{
  "status": "AVAILABLE"
}
```

### POST `/api/worker-schedule/v1/orders/sync-event`

Synchronizes order events to the schedule service.

Request:

```json
{
  "order_id": "ord-1001",
  "worker_id": "worker-1001",
  "worker_name": "王师傅",
  "event_type": "ASSIGNED",
  "start_time": "2026-04-08T10:00:00+08:00",
  "end_time": "2026-04-08T12:00:00+08:00",
  "title": "家庭深度保洁"
}
```

### GET `/api/worker-schedule/v1/schedule/daily`

Query parameter:
- `date`: required, example `2026-04-08`.

### GET `/api/worker-schedule/v1/orders/{order_id}`

Returns schedule detail for one order.

## Service Execution APIs

### POST `/api/service-execution/v1/orders/{order_id}/start`

Worker starts on-site service. This should move business state toward `IN_SERVICE` in downstream services.

Allowed roles: any authenticated role; intended role is `WORKER`.

Request:

```json
{
  "worker_id": "worker-1001",
  "started_at": "2026-04-08T10:05:00+08:00",
  "remark": "已到达客户现场"
}
```

Response:

```json
{
  "record": {
    "order_id": "ord-1001",
    "worker_id": "worker-1001",
    "status": "IN_SERVICE",
    "started_at": "2026-04-08T10:05:00+08:00",
    "completed_at": null,
    "actual_duration_minutes": null,
    "completion_note": null,
    "photos": []
  }
}
```

### POST `/api/service-execution/v1/orders/{order_id}/complete`

Worker completes service. This should move business state toward `COMPLETE` in downstream services.

Request:

```json
{
  "worker_id": "worker-1001",
  "completed_at": "2026-04-08T12:10:00+08:00",
  "actual_duration_minutes": 125,
  "completion_note": "深度保洁已完成，客户现场确认"
}
```

Response:

```json
{
  "record": {
    "order_id": "ord-1001",
    "worker_id": "worker-1001",
    "status": "COMPLETE",
    "started_at": "2026-04-08T10:05:00+08:00",
    "completed_at": "2026-04-08T12:10:00+08:00",
    "actual_duration_minutes": 125,
    "completion_note": "深度保洁已完成，客户现场确认",
    "photos": []
  }
}
```

### POST `/api/service-execution/v1/orders/{order_id}/photos`

Binds a service photo or voucher URL to an order. This API does not upload binary files.

Request:

```json
{
  "photo_url": "https://example.com/service-photos/ord-1001-after.jpg",
  "photo_type": "AFTER",
  "remark": "客厅清洁完成照片"
}
```

Response:

```json
{
  "photo": {
    "photo_id": "photo-1001",
    "order_id": "ord-1001",
    "photo_url": "https://example.com/service-photos/ord-1001-after.jpg",
    "photo_type": "AFTER",
    "remark": "客厅清洁完成照片",
    "uploaded_by": "worker-1001",
    "uploaded_at": "2026-04-08T12:05:00+08:00"
  }
}
```

### GET `/api/service-execution/v1/orders/{order_id}/record`

Returns the service execution archive for one order.

## Finance APIs

### GET `/api/finance/v1/invoices/{invoice_id}`

Legacy invoice lookup endpoint.

### POST `/api/finance/v1/orders/{order_id}/payments`

Customer service confirms that the customer has paid. This is a manual/mock payment confirmation API, not a real WeChat Pay integration.

Allowed roles: `CUSTOMER_SERVICE`, `OWNER`.

Request:

```json
{
  "amount": 26800,
  "currency": "CNY",
  "payment_method": "WECHAT",
  "paid_at": "2026-04-08T12:30:00+08:00",
  "remark": "客服已核对微信收款截图"
}
```

Response:

```json
{
  "payment": {
    "payment_id": "pay-1001",
    "order_id": "ord-1001",
    "amount": 26800,
    "currency": "CNY",
    "payment_method": "WECHAT",
    "payment_status": "PAID",
    "paid_at": "2026-04-08T12:30:00+08:00",
    "confirmed_by": "cs-1001",
    "remark": "客服已核对微信收款截图",
    "created_at": "2026-04-08T12:31:00+08:00"
  }
}
```

### GET `/api/finance/v1/orders/{order_id}/payments`

Lists payment records for one order.

Allowed roles: `CUSTOMER_SERVICE`, `OWNER`.

Response:

```json
{
  "payments": [
    {
      "payment_id": "pay-1001",
      "order_id": "ord-1001",
      "amount": 26800,
      "currency": "CNY",
      "payment_method": "WECHAT",
      "payment_status": "PAID",
      "paid_at": "2026-04-08T12:30:00+08:00",
      "confirmed_by": "cs-1001",
      "remark": "客服已核对微信收款截图",
      "created_at": "2026-04-08T12:31:00+08:00"
    }
  ]
}
```

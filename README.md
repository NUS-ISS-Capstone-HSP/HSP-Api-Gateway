# hsp-api-gateway

一个基于 Python 3.12 的 API Gateway：
- 外部入口：HTTP（FastAPI）
- 内部调用：gRPC（grpcio）
- 网关负责 JWT 校验、RBAC、统一错误、请求日志、身份 metadata 透传

## 项目结构

```text
app/
  main.py
  config.py
  errors.py
  middleware/
    auth.py
    request_id.py
  security/
    jwt_utils.py
  gateway/
    grpc_clients.py
    http_to_rpc_router.py
    metadata.py
protos/
scripts/gen_proto.sh
tests/
mock_services/
.env.example
Makefile
Dockerfile
docker-compose.yml
```

## 本地运行步骤

1. 创建虚拟环境并安装依赖：

```bash
conda create -n hsp-api-gateway python=3.12 -y
conda activate hsp-api-gateway
pip install -r requirements.txt
```

2. 准备环境变量：

```bash
cp .env.example .env
```

3. 启动网关（本地模式）：
本地用这个命令，环境变量是 .env.example
```bash
make run-local
```

4. 启动完整 Docker 联调环境（含 5 个 mock gRPC 服务）：

```bash
make docker-up
```

网关地址：`http://127.0.0.1:8081`

Swagger 文档地址：
- `http://127.0.0.1:8081/docs`
- `http://127.0.0.1:8081/redoc`

## Proto 生成命令

```bash
make gen-proto
# 或
bash scripts/gen_proto.sh
```

生成输出目录为 `generated/`。

## curl 示例

1. 健康检查（白名单，无需 token）：

```bash
curl -i http://127.0.0.1:8081/healthz
```

2. 登录（白名单，无需 token，转发到 user-service gRPC）：

```bash
curl -i -X POST http://127.0.0.1:8081/api/users/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"123456"}'
```

3. 生成测试 JWT（HS256）：

```bash
python - <<'PY'
import time, jwt
payload = {
  "sub": "u-1001",
  "email": "owner@example.com",
  "role": "OWNER",
  "iss": "hsp-user-service",
  "aud": "hsp-api",
  "exp": int(time.time()) + 3600,
}
print(jwt.encode(payload, "replace_me", algorithm="HS256"))
PY
```

4. 访问受保护路由：

```bash
TOKEN=<上一步输出>
curl -i -X POST http://127.0.0.1:8081/api/users/v1/orders/dispatch \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'x-user-role: OWNER' \
  -d '{"order_id":"ord-1"}'
```

说明：即便客户端伪造 `x-user-role/x-user-id`，网关也会丢弃同名 header，转而使用 JWT 解析出的身份写入 gRPC metadata。

5. 订单服务（已接入真实 `order.v1.OrderService`）：

```bash
TOKEN=<登录得到的access_token>

# 创建订单
curl -i -X POST http://127.0.0.1:8081/api/orders/v1/orders \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_name":"张三",
    "phone":"13800000000",
    "service_address":"上海市浦东新区XX路100号",
    "service_type":"CLEANING",
    "appointment_time":"2026-04-08T10:00:00+08:00",
    "estimated_duration_minutes":120
  }'

# 订单详情
curl -i "http://127.0.0.1:8081/api/orders/v1/orders/<order_id>" \
  -H "Authorization: Bearer ${TOKEN}"

# 订单列表
curl -i "http://127.0.0.1:8081/api/orders/v1/orders?page=1&page_size=20&status=ORDER_STATUS_CREATED" \
  -H "Authorization: Bearer ${TOKEN}"

# 状态流转
curl -i -X PATCH http://127.0.0.1:8081/api/orders/v1/orders/<order_id>/status \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"target_status":"ACCEPT","assigned_worker_id":"worker-1001"}'
```

6. 调度服务（已接入真实 `dispatch.v1.DispatchService`）：

```bash
TOKEN=<登录得到的access_token>

# 可分配师傅列表
curl -i "http://127.0.0.1:8081/api/dispatch/v1/workers/available?service_type=CLEANING&region=sh-pd&limit=10" \
  -H "Authorization: Bearer ${TOKEN}"

# 人工派单
curl -i -X POST http://127.0.0.1:8081/api/dispatch/v1/assignments/manual \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord-1001","worker_id":"worker-1001"}'

# 师傅待确认列表
curl -i "http://127.0.0.1:8081/api/dispatch/v1/worker/pending-dispatches" \
  -H "Authorization: Bearer ${TOKEN}"

# 师傅确认/拒绝
curl -i -X POST http://127.0.0.1:8081/api/dispatch/v1/dispatches/<dispatch_id>/confirm \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"response":"ACCEPT"}'

# 订单派单历史
curl -i "http://127.0.0.1:8081/api/dispatch/v1/orders/<order_id>/history" \
  -H "Authorization: Bearer ${TOKEN}"
```

7. 排班服务（已接入真实 `worker_schedule.v1.WorkerScheduleService`）：

```bash
TOKEN=<登录得到的access_token>

# 注册师傅
curl -i -X POST http://127.0.0.1:8081/api/worker-schedule/v1/workers/register \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"worker_id":"worker-1001","worker_name":"王师傅"}'

# 师傅列表
curl -i "http://127.0.0.1:8081/api/worker-schedule/v1/workers" \
  -H "Authorization: Bearer ${TOKEN}"

# 更新师傅状态
curl -i -X PATCH http://127.0.0.1:8081/api/worker-schedule/v1/workers/worker-1001/status \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"status":"IN_SERVICE"}'

# 同步订单事件到排班
curl -i -X POST http://127.0.0.1:8081/api/worker-schedule/v1/orders/sync-event \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "order_id":"ord-1001",
    "worker_id":"worker-1001",
    "worker_name":"王师傅",
    "event_type":"ASSIGNED",
    "start_time":"2026-04-07T10:00:00+08:00",
    "end_time":"2026-04-07T12:00:00+08:00",
    "title":"空调安装"
  }'

# 日排班
curl -i "http://127.0.0.1:8081/api/worker-schedule/v1/schedule/daily?date=2026-04-07" \
  -H "Authorization: Bearer ${TOKEN}"

# 订单排班详情
curl -i "http://127.0.0.1:8081/api/worker-schedule/v1/orders/ord-1001" \
  -H "Authorization: Bearer ${TOKEN}"
```

## Docker 网络中通过 service name 访问 gRPC

在 `docker-compose.yml` 中，网关与下游服务在同一网络 `hsp-net`。因此网关可直接通过 Docker DNS 访问：
- `user-service:50051`
- `order-service:50051`
- `dispatch-service:50051`
- `worker-schedule-service:50051`
- `finance-service:50051`

对应环境变量：
- `USER_GRPC_TARGET=user-service:50051`
- `ORDER_GRPC_TARGET=order-service:50051`
- `DISPATCH_GRPC_TARGET=dispatch-service:50051`
- `WORKER_SCHEDULE_GRPC_TARGET=worker-schedule-service:50051`
- `SERVICE_EXECUTION_GRPC_TARGET=service-execution-service:50051`
- `FINANCE_GRPC_TARGET=finance-service:50051`

## 完整 API 文档

面向“客服派单 -> 工人确认 -> 履约 -> 客服收款 -> 关单”集成测试的完整接口说明见：

- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## 鉴权与 RBAC 规则

- JWT HS256 校验：`signature/exp/iss/aud`
- Claims 要求：`sub/email/role`
- 白名单：
  - `/healthz`
  - `/api/users/v1/auth/register`
  - `/api/users/v1/auth/login`
- RBAC（网关执行）：
  - `WORKER` 禁止 `/api/users/v1/admin/*`
  - `/api/users/v1/orders/dispatch` 仅 `CUSTOMER_SERVICE` 与 `OWNER` 可访问

## 统一错误格式

```json
{
  "code": "FORBIDDEN",
  "message": "Role cannot dispatch orders",
  "request_id": "..."
}
```

并支持 gRPC 状态到 HTTP 映射，例如：
- `UNAUTHENTICATED -> 401`
- `PERMISSION_DENIED -> 403`
- `NOT_FOUND -> 404`
- `UNAVAILABLE -> 503`

## 可观测性

网关输出结构化 JSON 日志字段：
- `request_id`
- `path`
- `method`
- `status_code`
- `latency_ms`
- `user_id`

## 验收测试

执行：

```bash
make test
```

覆盖场景：
- 无 token 访问受保护路由 -> 401
- 非法 token -> 401
- WORKER 访问 admin -> 403
- CUSTOMER_SERVICE 访问 dispatch -> 成功
- 下游可收到 metadata 中 `x-user-id/x-user-role`
- gRPC `NOT_FOUND` -> HTTP 404

## 安全边界：为何下游不再验 JWT 仍可行

前提是严格执行以下边界：

1. 下游服务仅暴露在内网（Docker 私有网络），不对公网开放端口。  
2. 公网只开放 Gateway；所有外部请求必须先通过 Gateway。  
3. Gateway 丢弃客户端伪造身份头，仅用 JWT 校验后生成身份 metadata。  
4. 下游服务仅信任来自 Gateway 的流量与 metadata（可进一步叠加 mTLS / NetworkPolicy / 安全组限制）。

在该边界下，JWT 验证统一收口到 Gateway 可以减少重复逻辑，并保持身份链路一致。

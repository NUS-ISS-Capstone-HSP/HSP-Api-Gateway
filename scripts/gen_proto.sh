#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/generated"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python)}"
PROTO_INCLUDE="$("${PYTHON_BIN}" -c "import pathlib, grpc_tools; print(pathlib.Path(grpc_tools.__file__).resolve().parent / '_proto')")"

mkdir -p "${OUT_DIR}"
touch "${OUT_DIR}/__init__.py"

"${PYTHON_BIN}" -m grpc_tools.protoc \
  -I"${ROOT_DIR}/protos" \
  -I"${PROTO_INCLUDE}" \
  --python_out="${OUT_DIR}" \
  --grpc_python_out="${OUT_DIR}" \
  "${ROOT_DIR}/protos/user.proto" \
  "${ROOT_DIR}/protos/order.proto" \
  "${ROOT_DIR}/protos/dispatch.proto" \
  "${ROOT_DIR}/protos/worker_schedule.proto" \
  "${ROOT_DIR}/protos/service_execution.proto" \
  "${ROOT_DIR}/protos/finance.proto"

echo "Proto generation done -> ${OUT_DIR}"

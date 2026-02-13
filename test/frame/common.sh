#!/bin/bash
# ============================ common.sh 说明 ============================
#
# - 作用：测试框架公共函数库
# - 用法：source test/frame/common.sh
#
# ==============================================================================

TEST_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT_DIR="$(cd "${TEST_ROOT_DIR}/.." && pwd)"

print() { echo "[TEST] $*"; }

print_error() { echo "[TEST ERROR] $*" >&2; }

is_port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -i ":${port}" >/dev/null 2>&1
  elif command -v netstat >/dev/null 2>&1; then
    netstat -tuln 2>/dev/null | grep -q ":${port} "
  elif command -v ss >/dev/null 2>&1; then
    ss -tuln 2>/dev/null | grep -q ":${port} "
  else
    (echo >/dev/tcp/127.0.0.1/"${port}") 2>/dev/null
  fi
}

is_port_responding() {
  local url="$1"
  curl -fsS --max-time 1 "$url" >/dev/null 2>&1
}

wait_http_ok() {
  local url="$1"
  local name="$2"
  local tries="${3:-30}"
  local delay="${4:-1}"
  local i
  print "waiting for ${name} to be ready at ${url}..."
  for ((i=1; i<=tries; i++)); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      print "${name} ready! (after ${i} attempts)"
      return 0
    fi
    if (( i % 10 == 0 )); then
      echo -n "."
    fi
    sleep "$delay"
  done
  echo ""
  print_error "timeout waiting ${name}: ${url}"
  return 1
}

kill_pgid() {
  local pid="$1"
  local port="$2"
  if [[ -n "${pid}" ]]; then
    kill -TERM "--" "-${pid}" >/dev/null 2>&1 || true
    sleep 1 || true
    kill -KILL "--" "-${pid}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${port}" ]]; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  fi
}

check_ports_available() {
  local ports=("$@")
  for port in "${ports[@]}"; do
    if is_port_in_use "${port}"; then
      print_error "port ${port} is already in use"
      print "You can use: lsof -i :${port} to find the process"
      return 1
    fi
  done
  return 0
}

cleanup_data_vector_store() {
  rm -f  "${PROJECT_ROOT_DIR}/data/vector_store/metadata.json" 2>/dev/null || true
  rm -f  "${PROJECT_ROOT_DIR}/data/vector_store/article_embeddings.npz" 2>/dev/null || true
  rm -rf "${PROJECT_ROOT_DIR}/data/vector_store/faiss.index" 2>/dev/null || true
  rm -f  "${PROJECT_ROOT_DIR}/data/vector_store/"*.tmp 2>/dev/null || true
  rm -f  "${PROJECT_ROOT_DIR}/data/vector_store/"*.corrupt.* 2>/dev/null || true
}

run_python_test() {
  local test_file="$1"
  local log_file="$2"
  shift 2
  
  if [[ ! -f "${test_file}" ]]; then
    print_error "test file not found: ${test_file}"
    return 1
  fi
  
  print "running test: ${test_file}"
  if [[ -n "${log_file}" ]]; then
    python "${test_file}" "$@" 2>&1 | tee "${log_file}"
  else
    python "${test_file}" "$@"
  fi
}

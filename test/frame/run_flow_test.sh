#!/bin/bash
# ============================ run_flow_test.sh 说明 ============================
#
# - 作用：业务流程测试框架，启动所有相关组件
# - 用法：bash run_flow_test.sh [--vdb|--rag]
# - 注意：需要在沙箱外执行（因为llm_service需要GPU）
#
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
source "${TEST_ROOT_DIR}/config/test_env.sh"

LLM_PID=""
RAG_PID=""
RAGUI_PID=""
VDBUI_PID=""

cleanup() {
  set +e
  print "cleanup: stopping services"
  kill_pgid "${VDBUI_PID}" "${VDBUI_PORT}"
  kill_pgid "${RAGUI_PID}" "${RAGUI_PORT}"
  kill_pgid "${LLM_PID}" "${LLM_PORT}"
  kill_pgid "${RAG_PID}" "${RAG_PORT}"
  cleanup_data_vector_store
  print "cleanup: done"
}

trap cleanup EXIT

start_all_services() {
  print "starting llm_service"
  setsid bash -lc "${TEST_ROOT_DIR}/scripts/start_llm.sh" >"${TEST_ROOT_DIR}/log/llm.log" 2>&1 &
  LLM_PID="$!"
  print "llm_service pgid=${LLM_PID}"
  
  print "starting rag_app"
  setsid bash -lc "${TEST_ROOT_DIR}/scripts/start_rag_ui.sh --rag" >"${TEST_ROOT_DIR}/log/rag.log" 2>&1 &
  RAG_PID="$!"
  print "rag_app pgid=${RAG_PID}"
  
  print "starting ragui"
  setsid bash -lc "${TEST_ROOT_DIR}/scripts/start_rag_ui.sh --ragui" >"${TEST_ROOT_DIR}/log/ragui.log" 2>&1 &
  RAGUI_PID="$!"
  print "ragui pgid=${RAGUI_PID}"
  
  print "starting vdbui"
  setsid bash -lc "${TEST_ROOT_DIR}/scripts/start_rag_ui.sh --vdbui" >"${TEST_ROOT_DIR}/log/vdbui.log" 2>&1 &
  VDBUI_PID="$!"
  print "vdbui pgid=${VDBUI_PID}"
  
  wait_http_ok "${LLM_BASE}/health" "llm_service" "${STARTUP_TIMEOUT_LLM}" 1
  wait_http_ok "${RAG_BASE}/health" "rag_app" "${STARTUP_TIMEOUT_RAG}" 1
  wait_http_ok "${RAGUI_BASE}" "ragui" "${STARTUP_TIMEOUT_UI}" 1
  wait_http_ok "${VDBUI_BASE}" "vdbui" "${STARTUP_TIMEOUT_UI}" 1
}

start_rag_only() {
  print "starting rag_app"
  setsid bash -lc "${TEST_ROOT_DIR}/scripts/start_rag_ui.sh --rag" >"${TEST_ROOT_DIR}/log/rag.log" 2>&1 &
  RAG_PID="$!"
  print "rag_app pgid=${RAG_PID}"
  
  wait_http_ok "${RAG_BASE}/health" "rag_app" "${STARTUP_TIMEOUT_RAG}" 1
}

test_vdb_flow() {
  print "running VDB flow tests"
  run_python_test "${TEST_ROOT_DIR}/case/flow/test_vdb_flow.py" "${TEST_ROOT_DIR}/log/flow/test_vdb_flow.log"
}

test_rag_flow() {
  print "running RAG flow tests"
  run_python_test "${TEST_ROOT_DIR}/case/flow/test_rag_flow.py" "${TEST_ROOT_DIR}/log/flow/test_rag_flow.log"
}

main() {
  cd "${PROJECT_ROOT_DIR}"
  
  if [[ $# -eq 0 ]]; then
    print "usage: $0 [--vdb|--rag]"
    exit 2
  fi
  
  local test_type="$1"
  
  case "${test_type}" in
    --vdb)
      check_ports_available "${RAG_PORT}"
      start_rag_only
      test_vdb_flow
      ;;
    --rag)
      check_ports_available "${LLM_PORT}" "${RAG_PORT}" "${RAGUI_PORT}" "${VDBUI_PORT}"
      start_all_services
      test_rag_flow
      ;;
    *)
      print "usage: $0 [--vdb|--rag]"
      exit 2
      ;;
  esac
  
  print "flow tests completed successfully"
}

main "$@"

#!/bin/bash
# ============================ run_api_test.sh 说明 ============================
#
# - 作用：接口测试框架，只启动被测组件
# - 用法：bash run_api_test.sh [--llm|--rag|--vdb]
# - 注意：llm测试需要在沙箱外执行
#
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
source "${TEST_ROOT_DIR}/config/test_env.sh"

LLM_PID=""
RAG_PID=""

cleanup() {
  set +e
  print "cleanup: stopping services"
  kill_pgid "${LLM_PID}" "${LLM_PORT}"
  kill_pgid "${RAG_PID}" "${RAG_PORT}"
  cleanup_data_vector_store
  print "cleanup: done"
}

trap cleanup EXIT

start_llm() {
  print "starting llm_service"
  setsid bash -lc "${TEST_ROOT_DIR}/scripts/start_llm.sh" >"${TEST_ROOT_DIR}/log/llm.log" 2>&1 &
  LLM_PID="$!"
  print "llm_service pgid=${LLM_PID}"
  wait_http_ok "${LLM_BASE}/health" "llm_service" "${STARTUP_TIMEOUT_LLM}" 1
}

start_rag() {
  print "starting rag_app"
  setsid bash -lc "${TEST_ROOT_DIR}/scripts/start_rag_ui.sh --rag" >"${TEST_ROOT_DIR}/log/rag.log" 2>&1 &
  RAG_PID="$!"
  print "rag_app pgid=${RAG_PID}"
  wait_http_ok "${RAG_BASE}/health" "rag_app" "${STARTUP_TIMEOUT_RAG}" 1
}

test_llm_api() {
  print "running LLM API tests"
  run_python_test "${TEST_ROOT_DIR}/case/api/test_llm_api.py" "${TEST_ROOT_DIR}/log/api/test_llm_api.log"
}

test_rag_api() {
  print "running RAG API tests"
  run_python_test "${TEST_ROOT_DIR}/case/api/test_rag_api.py" "${TEST_ROOT_DIR}/log/api/test_rag_api.log"
}

test_vdb_api() {
  print "running VDB API tests"
  run_python_test "${TEST_ROOT_DIR}/case/api/test_vdb_api.py" "${TEST_ROOT_DIR}/log/api/test_vdb_api.log"
}

main() {
  cd "${PROJECT_ROOT_DIR}"
  
  if [[ $# -eq 0 ]]; then
    print "usage: $0 [--llm|--rag|--vdb]"
    exit 2
  fi
  
  local test_type="$1"
  
  case "${test_type}" in
    --llm)
      check_ports_available "${LLM_PORT}"
      start_llm
      test_llm_api
      ;;
    --rag)
      check_ports_available "${RAG_PORT}"
      start_rag
      test_rag_api
      ;;
    --vdb)
      check_ports_available "${RAG_PORT}"
      start_rag
      test_vdb_api
      ;;
    *)
      print "usage: $0 [--llm|--rag|--vdb]"
      exit 2
      ;;
  esac
  
  print "API tests completed successfully"
}

main "$@"

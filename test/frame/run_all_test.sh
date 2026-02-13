#!/bin/bash
# ============================ run_all_test.sh 说明 ============================
#
# - 作用：全量测试框架，执行所有测试类型
# - 用法：bash run_all_test.sh
# - 注意：需要在沙箱外执行（因为llm_service需要GPU）
#
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
source "${TEST_ROOT_DIR}/config/test_env.sh"

TEST_RESULT_DIR="${TEST_ROOT_DIR}/log/results"
mkdir -p "${TEST_RESULT_DIR}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${TEST_RESULT_DIR}/report_${TIMESTAMP}.txt"

print_report() {
  echo "$*" | tee -a "${REPORT_FILE}"
}

run_all_api_tests() {
  print_report "========== API Tests =========="
  
  print_report "--- LLM API Tests ---"
  if bash "${SCRIPT_DIR}/run_api_test.sh" --llm 2>&1 | tee -a "${REPORT_FILE}"; then
    print_report "[PASS] LLM API tests"
  else
    print_report "[FAIL] LLM API tests"
    return 1
  fi
  
  print_report "--- RAG API Tests ---"
  if bash "${SCRIPT_DIR}/run_api_test.sh" --rag 2>&1 | tee -a "${REPORT_FILE}"; then
    print_report "[PASS] RAG API tests"
  else
    print_report "[FAIL] RAG API tests"
    return 1
  fi
  
  print_report "--- VDB API Tests ---"
  if bash "${SCRIPT_DIR}/run_api_test.sh" --vdb 2>&1 | tee -a "${REPORT_FILE}"; then
    print_report "[PASS] VDB API tests"
  else
    print_report "[FAIL] VDB API tests"
    return 1
  fi
}

run_all_flow_tests() {
  print_report "========== Flow Tests =========="
  
  print_report "--- VDB Flow Tests ---"
  if bash "${SCRIPT_DIR}/run_flow_test.sh" --vdb 2>&1 | tee -a "${REPORT_FILE}"; then
    print_report "[PASS] VDB flow tests"
  else
    print_report "[FAIL] VDB flow tests"
    return 1
  fi
  
  print_report "--- RAG Flow Tests ---"
  if bash "${SCRIPT_DIR}/run_flow_test.sh" --rag 2>&1 | tee -a "${REPORT_FILE}"; then
    print_report "[PASS] RAG flow tests"
  else
    print_report "[FAIL] RAG flow tests"
    return 1
  fi
}

main() {
  cd "${PROJECT_ROOT_DIR}"
  
  print_report "========================================"
  print_report "RAG-Demo Full Test Report"
  print_report "Timestamp: ${TIMESTAMP}"
  print_report "========================================"
  
  local failed=0
  
  if ! run_all_api_tests; then
    failed=1
  fi
  
  if ! run_all_flow_tests; then
    failed=1
  fi
  
  print_report "========================================"
  if [[ ${failed} -eq 0 ]]; then
    print_report "ALL TESTS PASSED"
    print_report "========================================"
    exit 0
  else
    print_report "SOME TESTS FAILED"
    print_report "========================================"
    exit 1
  fi
}

main "$@"

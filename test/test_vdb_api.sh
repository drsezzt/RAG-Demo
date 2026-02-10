#!/bin/bash
# =========================== test_vdb_api.sh 说明 ===========================
#
# - 作用：一键启动 rag_app + vdbui，完整测试全部 FastAPI 接口，无论成败
#   最后都会自动停止服务并清理 data/vector_store 生成的文件。
#
# - 实现方式：
#   * shell：进程管理、环境启动、端口探测、失败后统一清理
#   * 内嵌 python：调用标准库 urllib 直接发送 /doc、/chat、/doc/{id} 请求
#     不依赖 requests，失败/断言即直接 `sys.exit(1)` 触发 outer shell 检测
#
# - 失败处理：trap + cleanup(); 任意步骤（curl、python、命令）异常都会
#   导致脚本以非 0 退出，同时停止两个后台进程组并删除所有临时文件。
# ===============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_SH="${ROOT_DIR}/scripts/run.sh"

LLM_HOST="127.0.0.1"
LLM_PORT="8001"
LLM_BASE="http://${LLM_HOST}:${LLM_PORT}"

RAG_HOST="127.0.0.1"
RAG_PORT="8000"
RAG_BASE="http://${RAG_HOST}:${RAG_PORT}"

VDBUI_HOST="127.0.0.1"
VDBUI_PORT="8502"
VDBUI_BASE="http://${VDBUI_HOST}:${VDBUI_PORT}"

LLM_HOST="127.0.0.1"
LLM_PORT="8001"
LLM_BASE="http://${LLM_HOST}:${LLM_PORT}"

DOC_NAME="api_test_$(date +%s)_${RANDOM}.txt"
DOC_TMP_PATH="/tmp/${DOC_NAME}"

RAG_PID=""
LLM_PID=""
VDBUI_PID=""

print() { echo "[test_vdb_api] $*"; }

# 探测端口是否已响应；成功返回 0，失败返回 1
is_port_responding() {
  local url="$1"
  curl -fsS --max-time 1 "$url" >/dev/null 2>&1
}

# 等待指定 url 能稳定返回 200，通常用于等待服务初始化
# 参数：url、服务名称、轮询次数、延迟(秒)
# 失败则直接 print 报错并以 1 退出
wait_http_ok() {
  local url="$1"
  local name="$2"
  local tries="${3:-60}"
  local delay="${4:-0.5}"
  local i
  print "waiting for ${name} to be ready at ${url}..."
  for ((i=1; i<=tries; i++)); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      print "${name} ready! (after ${i} attempts)"
      return 0
    fi
    if (( i % 10 == 0 )); then
      echo -n "." # 每10次探测打印一个点，表示还在运行
    fi
    sleep "$delay"
  done
  echo ""
  print "ERROR: timeout waiting ${name}: ${url}"
  
  # 探测失败时，尝试打印对应日志文件的最后10行，帮助定位问题
  local log_file=""
  case "${name}" in
    llm_service) log_file="${ROOT_DIR}/.llm.test.log" ;;
    rag_app) log_file="${ROOT_DIR}/.rag_app.test.log" ;;
    vdbui) log_file="${ROOT_DIR}/.vdbui.test.log" ;;
  esac
  if [[ -f "${log_file}" ]]; then
    print "Last 10 lines of ${log_file}:"
    tail -n 10 "${log_file}"
  fi
  return 1
}

kill_pgid() {
  local pid="$1"
  if [[ -z "${pid}" ]]; then
    return 0
  fi
  # Best-effort: kill process group created by setsid
  kill -TERM "--" "-${pid}" >/dev/null 2>&1 || true
  sleep 0.5 || true
  kill -KILL "--" "-${pid}" >/dev/null 2>&1 || true
}

cleanup_data_vector_store() {
  # Only remove generated artifacts; keep .gitkeep if present.
  rm -f  "${ROOT_DIR}/data/vector_store/metadata.json" 2>/dev/null || true
  rm -f  "${ROOT_DIR}/data/vector_store/article_embeddings.npz" 2>/dev/null || true
  rm -rf "${ROOT_DIR}/data/vector_store/faiss.index" 2>/dev/null || true
  rm -f  "${ROOT_DIR}/data/vector_store/"*.tmp 2>/dev/null || true
  rm -f  "${ROOT_DIR}/data/vector_store/"*.corrupt.* 2>/dev/null || true
}

cleanup() {
  set +e
  print "cleanup: stopping services (if started by this script)"
  kill_pgid "${VDBUI_PID}"
  kill_pgid "${LLM_PID}"
  kill_pgid "${RAG_PID}"

  print "cleanup: removing temp doc ${DOC_TMP_PATH}"
  rm -f "${DOC_TMP_PATH}" 2>/dev/null || true

  print "cleanup: removing test logs"
  rm -f "${ROOT_DIR}/.rag_app.test.log" "${ROOT_DIR}/.vdbui.test.log" "${ROOT_DIR}/.llm.test.log" 2>/dev/null || true

  print "cleanup: removing generated vector_store data"
  cleanup_data_vector_store

  print "cleanup: done"
}

trap cleanup EXIT

main() {
  cd "${ROOT_DIR}"

  DEBUG_HTTP=0
  while getopts ":d" opt; do
    case "$opt" in
      d) DEBUG_HTTP=1 ;;
      *) print "usage: $0 [-d]"; exit 2 ;;
    esac
  done
  shift $((OPTIND-1))

  if ! command -v curl >/dev/null 2>&1; then
    print "ERROR: curl not found"
    exit 1
  fi

  if [[ ! -x "${RUN_SH}" ]]; then
    print "ERROR: ${RUN_SH} not found or not executable"
    exit 1
  fi

  # Avoid clobbering an already-running environment.
  if is_port_responding "${LLM_BASE}/health"; then
    print "ERROR: ${LLM_BASE} already responding. Please stop existing llm_service first."
    exit 1
  fi
  if is_port_responding "${RAG_BASE}/doc"; then
    print "ERROR: ${RAG_BASE} already responding. Please stop existing rag_app first."
    exit 1
  fi
  if is_port_responding "${VDBUI_BASE}"; then
    print "ERROR: ${VDBUI_BASE} already responding. Please stop existing vdbui first."
    exit 1
  fi

  print "starting llm_service via run.sh"
  setsid bash -lc "${RUN_SH} --llm <<<''" >"${ROOT_DIR}/.llm.test.log" 2>&1 &
  LLM_PID="$!"
  print "llm_service pgid=${LLM_PID}"

  print "starting rag_app via run.sh"
  # - setsid 开启新的进程组，便于 cleanup 时整组 kill
  # - 输出到 .rag_app.test.log 方便定位启动错误；python 测试也可见
  setsid "${RUN_SH}" --rag >"${ROOT_DIR}/.rag_app.test.log" 2>&1 &
  RAG_PID="$!"
  print "rag_app pgid=${RAG_PID}"

  print "starting vdbui via run.sh"
  # Streamlit may prompt for email; provide empty input to avoid hanging.
  setsid bash -lc "${RUN_SH} --vdbui <<<''" >"${ROOT_DIR}/.vdbui.test.log" 2>&1 &
  VDBUI_PID="$!"
  print "vdbui pgid=${VDBUI_PID}"

  wait_http_ok "${LLM_BASE}/health" "llm_service" 240 0.5
  wait_http_ok "${RAG_BASE}/doc" "rag_app" 120 0.5
  wait_http_ok "${VDBUI_BASE}" "vdbui" 120 0.5

  print "running API tests against ${RAG_BASE}"
  TEST_DATA_PATH="${ROOT_DIR}/test/test_data.txt"
  if [[ ! -f "${TEST_DATA_PATH}" ]]; then
    print "ERROR: test data file not found: ${TEST_DATA_PATH}"
    exit 1
  fi
  DEBUG_HTTP="${DEBUG_HTTP}" TEST_DATA_PATH="${TEST_DATA_PATH}" python - <<'PY'
# 这个内联 python 负责测试 rag_app 的 FastAPI 四大接口：
# 1. GET /doc      初始列表（应为空）
# 2. POST /doc     上传新文档
# 3. GET /doc      添加后验证列表变更
# 4. POST /chat    基于新文档做问答
# 5. DELETE /doc   删除指定文档
# 6. GET /doc      再次确认列表已为空
#
# 失败(异常/assert)都会触发 outer shell 的 `set -e`，从而执行 cleanup。
# 测试仅依赖 python3 标准库（urllib、json、time、sys）。

import json, sys, time, urllib.request, urllib.error
import os

DEBUG = os.environ.get("DEBUG_HTTP") == "1"
BASE = "http://127.0.0.1:8000"
DOC_NAME = None

def _short(x, n=300):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + f"...(truncated,len={len(s)})"

def http_json(method: str, path: str, payload=None, timeout=10):
    url = BASE + path
    if DEBUG:
        print(f"[DEBUG] -> {method} {url} payload={_short(payload)}", flush=True)
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if DEBUG:
                print(f"[DEBUG] <- {resp.status} {resp.url}", flush=True)
            body = resp.read().decode("utf-8")
            try:
                j = json.loads(body) if body else None
            except Exception:
                j = None
            if DEBUG:
                print(f"[DEBUG] <- body={_short(body)}", flush=True)
            return resp.status, j, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return e.code, None, body

def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)

def step(name, fn):
    print(f"[API] {name} ...", flush=True)
    fn()
    print(f"[API] {name} OK", flush=True)

state = {"file_id": None, "docs": None}

def test_get_doc_empty():
    code, j, body = http_json("GET", "/doc")
    assert_true(code == 200, f"GET /doc status={code} body={body}")
    assert_true(isinstance(j, dict) and "docs" in j, f"GET /doc invalid json: {j}")
    assert_true(isinstance(j["docs"], list), f"GET /doc docs not list: {type(j['docs'])}")
    state["docs"] = j["docs"]

def test_add_doc():
    global DOC_NAME
    doc_path = os.environ.get("TEST_DATA_PATH")
    if not doc_path or not os.path.isfile(doc_path):
        raise AssertionError(f"TEST_DATA_PATH not set or file not found: {doc_path}")
    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()
    DOC_NAME = "test_data.txt"
    code, j, body = http_json("POST", "/doc", {"name": DOC_NAME, "content": content}, timeout=120)
    assert_true(code == 200, f"POST /doc status={code} body={body}")
    assert_true(isinstance(j, dict) and j.get("status") == "ok", f"POST /doc failed: {j} body={body}")

def test_get_doc_after_add():
    code, j, body = http_json("GET", "/doc")
    assert_true(code == 200, f"GET /doc status={code} body={body}")
    docs = j.get("docs") if isinstance(j, dict) else None
    assert_true(isinstance(docs, list), f"GET /doc docs invalid: {j}")
    hit = None
    for d in docs:
        if isinstance(d, dict) and d.get("filename") == DOC_NAME:
            hit = d
            break
    assert_true(hit is not None, f"doc not found after add: filename={DOC_NAME} docs_count={len(docs)}")
    file_id = hit.get("file_id")
    assert_true(isinstance(file_id, str) and file_id, f"invalid file_id in doc: {hit}")
    state["file_id"] = file_id

# 针对《中华人民共和国专利法》的五个 chat 测试用例（法条检索与问答）
CHAT_CASES = [
    "专利法所称的发明创造包括哪几种类型？",
    "申请专利的发明创造涉及国家安全或重大利益需要保密的，应当如何处理？",
    "职务发明创造申请专利的权利归属如何规定？",
    "同样的发明创造只能授予一项专利权，请简述相关规定。",
    "未经专利权人许可实施其专利即侵犯专利权，哪些情形不视为侵权？",
]

def test_chat():
    for i, text in enumerate(CHAT_CASES, 1):
        code, j, body = http_json("POST", "/chat", {"text": text}, timeout=90)
        assert_true(code == 200, f"POST /chat case {i} status={code} body={body}")
        assert_true(isinstance(j, dict) and isinstance(j.get("response"), str),
                    f"POST /chat case {i} invalid response: {j} body={body}")
        if DEBUG:
            print(f"[DEBUG] chat case {i} response={_short(j.get('response'))}", flush=True)

def test_delete_doc():
    file_id = state["file_id"]
    assert_true(file_id, "missing file_id before delete")
    code, j, body = http_json("DELETE", f"/doc/{file_id}", timeout=60)
    assert_true(code == 200, f"DELETE /doc/{{id}} status={code} body={body}")
    assert_true(isinstance(j, dict) and j.get("status") == "ok", f"DELETE failed: {j} body={body}")

def test_get_doc_after_delete():
    code, j, body = http_json("GET", "/doc")
    assert_true(code == 200, f"GET /doc status={code} body={body}")
    docs = j.get("docs") if isinstance(j, dict) else None
    assert_true(isinstance(docs, list), f"GET /doc docs invalid: {j}")
    for d in docs:
        if isinstance(d, dict) and d.get("file_id") == state["file_id"]:
            raise AssertionError(f"doc still exists after delete: {d}")

try:
    step("GET /doc (initial)", test_get_doc_empty)
    step("POST /doc (add)", test_add_doc)
    step("GET /doc (after add)", test_get_doc_after_add)
    step("POST /chat (5 cases)", test_chat)
    step("DELETE /doc/{id}", test_delete_doc)
    step("GET /doc (after delete)", test_get_doc_after_delete)
except Exception as e:
    print(f"[API] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(1)

print("[API] ALL TESTS PASSED")
PY

  print "tests completed successfully"
}

main "$@"


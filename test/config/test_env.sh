#!/bin/bash
# ============================ test_env.sh 说明 ============================
#
# - 作用：测试环境变量配置
# - 用法：source test/config/test_env.sh
#
# ==============================================================================

export LLM_HOST="127.0.0.1"
export LLM_PORT="8001"
export LLM_BASE="http://${LLM_HOST}:${LLM_PORT}"

export RAG_HOST="127.0.0.1"
export RAG_PORT="8000"
export RAG_BASE="http://${RAG_HOST}:${RAG_PORT}"

export RAGUI_HOST="127.0.0.1"
export RAGUI_PORT="8501"
export RAGUI_BASE="http://${RAGUI_HOST}:${RAGUI_PORT}"

export VDBUI_HOST="127.0.0.1"
export VDBUI_PORT="8502"
export VDBUI_BASE="http://${VDBUI_HOST}:${VDBUI_PORT}"

export STARTUP_TIMEOUT_LLM=60
export STARTUP_TIMEOUT_RAG=30
export STARTUP_TIMEOUT_UI=30

export API_TIMEOUT=30
export CHAT_TIMEOUT=90
export DOC_TIMEOUT=120

export TEST_DATA_NAME="test_data.txt"

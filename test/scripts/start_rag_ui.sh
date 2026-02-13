#!/bin/bash
# ============================ start_rag_ui.sh 说明 ============================
#
# - 作用：启动rag_app和ui组件（rag、ragui、vdbui）
# - 执行环境：沙箱内执行（不需要GPU访问）
# - 用法：bash start_rag_ui.sh [--rag|--ragui|--vdbui]
#
# ==============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

source ~/miniconda3/etc/profile.d/conda.sh

case "$1" in
    --rag)
        conda activate rag_runtime
        export PYTHONPATH="${ROOT_DIR}"
        python -m rag_app.main
        ;;
    --ragui)
        conda activate ui_runtime
        export PYTHONPATH="${ROOT_DIR}"
        streamlit run ui/rag_gui.py --server.port 8501
        ;;
    --vdbui)
        conda activate ui_runtime
        export PYTHONPATH="${ROOT_DIR}"
        streamlit run ui/vdb_gui.py --server.port 8502
        ;;
    *)
        echo "RAG和UI组件启动脚本"
        echo "用法: $0 [--rag|--ragui|--vdbui]"
        echo ""
        echo "选项:"
        echo "  --rag      启动RAG后端服务"
        echo "  --ragui    启动RAG UI (端口8501)"
        echo "  --vdbui    启动向量数据库UI (端口8502)"
        exit 1
        ;;
esac

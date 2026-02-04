#!/bin/bash
set -e  # 遇到错误立即退出

export PYTHONPATH=$(pwd)

# 初始化conda
CONDA_EXEC="$(conda info --base)/etc/profile.d/conda.sh"
[ -f "$CONDA_EXEC" ] && source "$CONDA_EXEC" || {
    echo "错误: 找不到conda初始化脚本"
    exit 1
}

activate_env() {
    local env_name="$1"

    # 检查环境是否存在
    if ! conda env list | grep -q "^$env_name "; then
        echo "错误: Conda环境 '$env_name' 不存在"
        echo "可用环境:"
        conda env list
        exit 1
    fi

    # 只有不在目标环境时才切换
    if [ "$CONDA_DEFAULT_ENV" != "$env_name" ]; then
        conda activate "$env_name"
        if [ $? -ne 0 ]; then
            echo "错误: 无法激活环境 '$env_name'"
            exit 1
        fi
    fi
}

case "$1" in
    --ragui)
        activate_env "ui_runtime"
        streamlit run ui/rag_gui.py --server.port 8501
        ;;
    --vdbui)
        activate_env "ui_runtime"
        streamlit run ui/vdb_gui.py --server.port 8502
        ;;
    --rag)
        activate_env "rag_runtime"
        python -m rag_app.main
        ;;
    --llm)
        activate_env "llm_runtime"
        python -m llm_service.main
        ;;
    *)
        echo "RAG系统启动脚本"
        echo "用法: $0 [--ragui|--vdbui|--rag|--llm]"
        echo ""
        echo "选项:"
        echo "  --ragui    启动RAG UI (端口8501)"
        echo "  --vdbui    启动向量数据库UI (端口8502)"
        echo "  --rag      启动RAG后端服务"
        echo "  --llm      启动LLM服务"
        exit 1
        ;;
esac
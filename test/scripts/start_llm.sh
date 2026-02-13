#!/bin/bash
# ============================ start_llm.sh 说明 ============================
#
# - 作用：启动llm_service组件，需要GPU访问
# - 执行环境：沙箱外执行（因为需要GPU访问）
# - 用法：bash start_llm.sh
#
# ==============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

source ~/miniconda3/etc/profile.d/conda.sh
conda activate llm_runtime

export PYTHONPATH="${ROOT_DIR}"
python -m llm_service.main

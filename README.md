# RAG-Demo

## 项目简介

`RAG-Demo` 是一个基于 RAG（Retrieval-Augmented Generation）技术的实验项目，旨在帮助开发者快速学习和应用 RAG 的核心概念和技术栈。该项目实现了一个简易的 RAG 工作流，结合了文档检索与生成技术。

## 主要功能

- **文档检索**：根据用户输入的问题，从知识库中检索相关文档。
- **问答生成**：基于原始问题和检索到的文档，生成合适的答案。
- **多用户支持**：支持多用户并发访问，提供隔离和安全的服务。（完成中）
- **容器化部署**：通过 Docker 容器化，可方便地在多种环境（如本地、云、边缘）上部署。
- **可扩展性**：支持新模型的集成，支持自定义知识库。

## 项目架构

本项目采用分布式架构，包含以下主要组件：

| 组件 | 说明 | 端口 | 依赖 |
|------|------|------|------|
| llm_service | 大语言模型服务，提供推理能力 | 8001 | GPU |
| rag_app | RAG业务服务，管理向量库和对话 | 8000 | llm_service |
| ui/rag_gui | RAG对话界面 | 8501 | rag_app |
| ui/vdb_gui | 向量库管理界面 | 8502 | rag_app |

### 系统架构图

```
知识问答流程：
User -> rag_gui (8501) -> rag_app (8000) -> llm_service (8001)

知识库管理流程：
User -> vdb_gui (8502) -> rag_app (8000) -> FAISS向量库
```

## 环境要求

- Python 3.10+
- CUDA 11.8+ (GPU支持)
- Docker 和 Docker Compose（容器化部署）
- Miniconda 或 Anaconda

## 项目目录结构

```
RAG-Demo/
├── config/                 # 项目配置文件
├── data/                   # 数据文件（向量库等）
├── libs/                   # 公共工具库
├── llm_service/            # LLM服务代码
├── rag_app/                # RAG系统服务代码
├── scripts/                # 项目脚本文件（非测试场景）
├── shared/                 # 共享配置类
├── test/                   # 测试模块
├── ui/                     # 用户界面代码
├── .gitignore
├── docker-compose.gpu.yml  # Docker配置（GPU版本）
├── docker-compose.yml      # Docker配置（CPU版本）
├── LICENSE
└── README.md
```

## 环境配置

### Conda环境

项目使用三个独立的Conda环境：

| 环境名 | 组件 | 激活命令 |
|--------|------|----------|
| llm_runtime | llm_service | `conda activate llm_runtime` |
| rag_runtime | rag_app | `conda activate rag_runtime` |
| ui_runtime | ui | `conda activate ui_runtime` |

### 安装依赖

```bash
# 克隆项目
git clone git@github.com:drsezzt/RAG-Demo.git
cd RAG-Demo

# 创建并激活LLM环境
conda create -n llm_runtime python=3.10
conda activate llm_runtime
pip install -r llm_service/requirements.txt

# 创建并激活RAG环境
conda create -n rag_runtime python=3.10
conda activate rag_runtime
pip install -r rag_app/requirements.txt

# 创建并激活UI环境
conda create -n ui_runtime python=3.10
conda activate ui_runtime
pip install -r ui/requirements.txt
```

## 组件启动

### 本地运行（非测试场景）

使用 `scripts/run.sh` 启动各组件：

```bash
# 启动LLM服务（需要GPU）
conda activate llm_runtime
bash scripts/run.sh --llm

# 启动RAG服务
conda activate rag_runtime
bash scripts/run.sh --rag

# 启动RAG对话界面
conda activate ui_runtime
bash scripts/run.sh --ragui

# 启动向量库管理界面
conda activate ui_runtime
bash scripts/run.sh --vdbui
```

### Docker容器运行

```bash
# GPU版本
docker compose -f docker-compose.gpu.yml build
docker compose -f docker-compose.gpu.yml up

# CPU版本
docker compose build
docker compose up
```

---

# 测试模块

本项目包含完整的测试模块，支持接口测试和业务流程测试。

## 测试目录结构

```
test/
├── log/          # 测试日志和结果
├── frame/        # 测试框架脚本
│   ├── common.sh          # 公共函数库
│   ├── run_api_test.sh    # 接口测试框架
│   ├── run_flow_test.sh   # 业务流程测试框架
│   └── run_all_test.sh    # 全量测试框架
├── case/         # 测试用例脚本
│   ├── api/      # 接口测试用例
│   ├── flow/     # 业务流程测试用例
│   └── common/   # 公共测试工具
├── config/       # 测试配置
└── scripts/      # 测试启动脚本
```

## 测试执行方式

### 最小范围测试

只测试特定组件或功能：

```bash
# 只测试LLM接口
bash test/frame/run_api_test.sh --llm

# 只测试RAG接口
bash test/frame/run_api_test.sh --rag

# 只测试VDB接口
bash test/frame/run_api_test.sh --vdb

# 只测试VDB业务流程
bash test/frame/run_flow_test.sh --vdb

# 只测试RAG业务流程
bash test/frame/run_flow_test.sh --rag
```

### 全量测试

执行所有测试：

```bash
bash test/frame/run_all_test.sh
```

## 测试配置

测试配置在 `test/config/test_env.sh` 中定义。

## 测试日志

测试日志保存在 `test/log/` 目录下。

---

## 技术栈

- 语言模型：Huggingface Transformers、ChatGLM3-6B、chatglm.cpp
- 向量数据库：FAISS
- Web框架：Streamlit、FastAPI
- 容器化：Docker、Docker Compose
- 测试框架：Bash、Python

# RAG-Demo

## 项目简介
`RAG-Demo` 是一个基于 RAG（Retrievel-Augmented Generation）技术的实验项目，旨在帮助开发者快速学习和应用 RAG 的核心概念和技术栈。该项目实现了一个简易的 RAG 工作流，结合了文档检索与生成技术。

## 主要功能
- **文档检索**：根据用户输入的问题，从知识库中检索相关文档。
- **问答生成**：基于原始问题和检索到的文档，生成合适的答案。
- **多用户支持**：支持多用户并发访问，提供隔离和安全的服务。（完成中）
- **容器化部署**：通过 Docker 容器化，可方便地在多种环境（如本地、云、边缘）上部署。
- **可扩展性**：支持新模型的集成，支持自定义知识库。

## 项目架构
本项目包含以下主要组件：
- **llm_service**: 用于加载和运行大语言模型，提供生成服务。
- **rag_app**: 管理向量数据库，进行文档检索和回答生成。
- **ui**: 提供知识问答和知识库管理的Web GUI界面。
- **libs**: 包含组件间公共代码，包含数据传输结构和工具函数等。

## 系统架构
知识问答：User->Streamlit(rag_gui)->rag_app->llm_service
知识库管理：User->Streamlit(vdb_gui)->rag_app(vector_db)

## 安装与运行
### 环境要求
- Python 3.10+
- Docker 和 Docker Compose（容器化部署）

### 拉取项目
    ```bash
    git clone git@github.com:drsezzt/RAG-Demo.git
    cd RAG-Demo
    ```

### 本地运行
    ```bash
    # 创建LLM虚拟运行环境，运行llm_service组件
    conda create -n llm_runtime python=3.10
    conda activate llm_runtime
    pip install -r llm_service/requirements.txt
    ./scripts/run.sh --llm

    # 创建RAG虚拟运行环境，运行rag_app组件
    conda create -n rag_runtime python=3.10
    conda activate rag_runtime
    pip install -r rag_app/requirements.txt
    ./scripts/run.sh --rag

    # 创建UI虚拟运行环境，运行ui组件
    conda create -n ui_runtime python=3.10
    conda activate ui_runtime
    pip install -r ui/requirements.txt
    ./scripts/run.sh --ragui
    ./scripts/run.sh --vdbui
    ```

### Docker容器运行
    ```bash
    docker compose build
    docker compose up
    ```

## 项目目录结构
    ```perl
    RAG-Demo/
    ├── config/                 # 项目配置文件
    ├── data/                   # 数据文件
    ├── libs/                   # 公共工具库
    ├── llm_service/            # LLM 相关服务代码
    ├── rag_app/                # RAG 系统服务代码
    ├── scripts/                # 项目脚本文件
    ├── ui/                     # 用户界面相关代码
    ├── .gitignore              # Git 忽略文件
    ├── docker-compose.gpu.yml  # Docker Compose配置文件（GPU版本）
    ├── docker-compose.yml      # Docker Compose配置文件（CPU版本）
    ├── LICENSE                 # 许可证
    └── README.md               # GitHub 仓库说明
    ```

## 技术栈
- 语言模型：Huggingface Transformers、ChatGLM3-6B、chatglm.cpp
- 向量数据库：FAISS
- Web框架：Streamlit、FastAPI
- 容器化：Docker、Docker Compose

## TODO
- 添加详细的调试日志和性能监控
- 支持多用户并发访问（完善用户认证和授权功能）
- 支持多个模型切换（比如更换不同的 LLM）
- 支持云端部署（完成云端配置和部署指南）

"""
RAG service interface for vector database management, document retrieval, and answer generation.
"""
import json

from fastapi import FastAPI, Request, Depends

from libs.utils.logger import init_component_logger
from libs.settings import AppConfig
from libs.protocols.rag_contract import ChatRequest, ChatResponse
from libs.protocols.vdb_contract import GetDocListResponse, AddDocRequest, CommonResponse
from rag_app.core.container import DIContainer
from rag_app.core.interface import IVectorStoreService


logger = init_component_logger("RAG_APP")
config = AppConfig.load("config/config.yaml")

container = DIContainer(config.model_dump())

async def lifespan(app: FastAPI):
    logger.info("op=rag_app_begin")

    app.state.container = container

    # 初始化LLM客户端
    app.state.rag_service = container.get_rag_service()

    # 初始化向量库服务
    app.state.vdb_service = container.get_vector_store_service()
    logger.info("op=rag_app_initialized")

    yield

    logger.info("op=rag_app_finish")

app = FastAPI(
    title="RAGSystem API",
    description="RAGSystem API",
    version="1.0.0",
    lifespan=lifespan
)

# 依赖函数
def get_vector_store_service(request: Request) -> IVectorStoreService:
    """获取向量存储服务依赖"""
    return request.app.state.vdb_service

def get_rag_service(request: Request):
    """获取 RAG 服务依赖"""
    return request.app.state.rag_service

# 问答接口
@app.post("/chat", response_model=ChatResponse)
async def chat(
    chat_in: ChatRequest,
    rag_service = Depends(get_rag_service)
):
    logger.info(
        "op=chat_start "
        f"text={chat_in.text}"
    )

    try:
        answer = rag_service.call_rag_flow(chat_in.text)
        logger.info(
            "op=chat_end "
            f"answer={answer}"
        )
        return ChatResponse(response=answer)
    except Exception as e:
        logger.exception(
            "op=chat_error "
            f"error={type(e).__name__}"
        )
        return ChatResponse(response="系统繁忙，请稍后再试。")

# 获取所有文档
@app.get("/doc", response_model=GetDocListResponse)
async def get_doc_list(
    vdb_service: IVectorStoreService = Depends(get_vector_store_service)
):
    logger.info("op=get_doc_list_start")
    try:
        metas = vdb_service.list_files()
        docs = [meta.model_dump() for meta in metas]
        logger.info(
            "op=get_doc_list_end "
            f"doc_count={len(docs)}"
        )
        return GetDocListResponse(docs=docs)
    except Exception as e:
        logger.exception(
            "op=get_doc_list_exception "
            f"exception={type(e).__name__}"
        )
        return GetDocListResponse()

# 删除文档
@app.delete("/doc/{doc_id}", response_model=CommonResponse)
async def delete_doc(
    doc_id: str,
    vdb_service: IVectorStoreService = Depends(get_vector_store_service)
):
    logger.info("op=delete_doc_start")
    try:
        if vdb_service.delete_file(doc_id):
            logger.info("op=delete_doc_end")
            return CommonResponse(status="ok")
        logger.error("op=delete_doc_error")
        return CommonResponse(status="error")
    except Exception as e:
        logger.exception(
            "op=delete_doc_exception "
            f"exception={type(e).__name__}"
        )
        return CommonResponse(status="error")

# 添加文档
@app.post("/doc", response_model=CommonResponse)
async def add_doc(
    param_in: AddDocRequest,
    vdb_service: IVectorStoreService = Depends(get_vector_store_service)
):
    logger.info(
        "op=add_doc_start "
        f"doc_name={param_in.name}"
    )
    try:
        tmp_path = "/tmp/" + param_in.name
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(param_in.content)
        if vdb_service.add_file(tmp_path):
            logger.info("op=add_doc_end")
            return CommonResponse(status="ok")
        logger.error("op=add_doc_error")
        return CommonResponse(status="error")
    except Exception as e:
        logger.exception(
            "op=add_doc_exception "
            f"exception={type(e).__name__}"
        )
        return CommonResponse(status="error")

if __name__ == "__main__":
    import uvicorn

    host = config.rag.host
    port = config.rag.port
    logger.info(
        "op=uvicorn_start "
        f"host={host} "
        f"port={port}"
    )
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
    logger.info("op=uvicorn_running")

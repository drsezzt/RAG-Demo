"""
RAG service interface for vector database management, document retrieval, and answer generation.
"""
import json

from fastapi import FastAPI, Request

from libs.utils.logger import init_component_logger
from libs.settings import AppConfig
from libs.protocols.rag_contract import ChatRequest, ChatResponse
from libs.protocols.vdb_contract import GetDocListResponse, AddDocRequest, CommonResponse
from rag_app.libs.utils import get_embeddings
from rag_app.core.llm_client import LLMClient
from rag_app.services.rag_service import RAGService
from rag_app.vector_store.service import VectorStoreService
from rag_app.vector_store.raw_faiss.store import FaissVectorStore
from rag_app.vector_store.metadata import MetadataRepository

logger = init_component_logger("RAG_APP")
config = AppConfig.load("config/config.yaml")

async def lifespan(app: FastAPI):
    logger.info("op=rag_app_begin")

    # 初始化LLM客户端
    url = "http://" + config.llm.host + ":" + str(config.llm.port)
    logger.info(f"op=app_set_llm_start url={url}")
    app.state.llm = LLMClient(url)
    logger.info("op=app_set_llm_done")

    # 初始化向量库
    index_path = config.vector_store.index_path
    logger.info(f"op=vdb_store_init_start path={index_path}")
    vdb_store = FaissVectorStore(
        dim=512,
        store_dir=index_path,
    )
    logger.info("op=vdb_store_init_done")

    # 初始化元数据管理
    meta_path = config.vector_store.meta_path
    logger.info(f"op=vdb_meta_init_start path={meta_path}")
    metadata = MetadataRepository(
        path=meta_path,
    )
    logger.info("op=vdb_meta_init_done")

    # 初始化向量库服务
    embed_path=config.vector_store.embed_path
    logger.info("op=vdb_service_init_start")
    app.state.vdb_service = VectorStoreService(
        store=vdb_store,
        metadata=metadata,
        embedder=get_embeddings(),
        embed_path=embed_path,
    )
    logger.info("op=vdb_service_init_done")

    yield

    logger.info("op=rag_app_finish")

app = FastAPI(
    title="RAGSystem API",
    description="RAGSystem API",
    version="1.0.0",
    lifespan=lifespan
)

# 问答接口
@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, chat_in: ChatRequest):
    logger.info(
        "op=chat_start "
        f"text={chat_in.text}"
    )
    service = RAGService(request.app.state.llm, request.app.state.vdb_service)
    try:
        answer = service.call_rag_flow(chat_in.text)
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
async def get_doc_list(request: Request):
    logger.info("op=get_doc_list_start")
    service = request.app.state.vdb_service
    try:
        metas = service.list_files()
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
async def delete_doc(request: Request, doc_id: str):
    logger.info("op=delete_doc_start")
    service = request.app.state.vdb_service
    try:
        if service.delete_file(doc_id):
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
async def add_doc(request: Request, param_in: AddDocRequest):
    logger.info(
        "op=add_doc_start "
        f"doc_name={param_in.name}"
    )
    service = request.app.state.vdb_service
    try:
        tmp_path = "/tmp/" + param_in.name
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(param_in.content)
        if service.add_file(tmp_path):
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

# FastAPI接入层
# 职责：API的端点定义、中间件配置和全局异常处理，不关心如何检索
#      和如何解析JSON，只负责HTTP->Python对象的协议转换

from libs.protocols.rag_contract import ChatRequest, ChatResponse
from libs.protocols.vdb_contract import GetLawListResponse, AddLawRequest, CommonResponse
from libs.utils.logger import init_component_logger
from rag_app.core.manager import VectorManager
from rag_app.core.llm_client import LLMClient
from fastapi import FastAPI, Request
from rag_app.libs.utils import get_embeddings
from rag_app.services.rag_service import RAGService
import os

logger = init_component_logger("RAG_APP")
logger.info("RAG 主服务启动...")

LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:8001")
VDB_PATH = "rag_app/vector_db/faiss_index"          # 向量数据库路径

# 向量库检查
def check_vdb(vdb):
    # 1. 查看库中有多少个向量
    vector_count = vdb.index.ntotal
    print(f"向量总数: {vector_count}")

    # 2. 查看向量的维度 (例如 768 或 1024)
    dimension = vdb.index.d
    print(f"向量维度: {dimension}")

    # 3. 查看 docstore 里的第一个文档（抽样检查）
    # 注意：vdb.docstore._dict 是存储数据的私有字典
    for sample_id in list(vdb.index_to_docstore_id.values()):
        sample_doc = vdb.docstore.search(sample_id)
        print(f"样本文档内容: {sample_doc.page_content[:50]}...")
        print(f"样本文档元数据: {sample_doc.metadata}")

async def lifespan(app: FastAPI):
    # 启动时加载
    app.state.llm = LLMClient(LLM_API_URL)
    app.state.manager = VectorManager(VDB_PATH, get_embeddings())
    if app.state.manager.vdb is not None:
        check_vdb(app.state.manager.vdb)

    yield

app = FastAPI(
    title="RAGSystem API",
    description="RAGSystem API",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, chat_in: ChatRequest):
    service = RAGService(request.app.state.llm, request.app.state.manager.vdb)
    try:
        answer = service.call_rag_flow(chat_in.text)
        return ChatResponse(response=answer)
    except Exception as e:
        logger.error(f"RAG Flow Failed: {e}")
        return ChatResponse(response="系统繁忙，请稍后再试。", status="error")

@app.get("/law", response_model=GetLawListResponse)
async def get_law_list(request: Request):
    manager = request.app.state.manager
    try:
        laws = manager.get_supported_laws()
        return GetLawListResponse(laws=laws)
    except Exception as e:
        logger.error(f"VDB Get Laws Failed: {e}")
        return GetLawListResponse()

@app.delete("/law/{law_name}", response_model=CommonResponse)
async def delete_law(request: Request, law_name: str):
    manager = request.app.state.manager
    try:
        if manager.delete_law(law_name):
            return CommonResponse(status="success")
        return CommonResponse(status="error")
    except Exception as e:
        logger.error(f"VDB Delete Law Failed: {e}")
        return CommonResponse(status="error")

@app.post("/law", response_model=CommonResponse)
async def add_law(request: Request, param_in: AddLawRequest):
    manager = request.app.state.manager
    try:
        if manager.add_new_law(param_in.name, param_in.content):
            return CommonResponse(status="success")
        return CommonResponse(status="error")
    except Exception as e:
        logger.error(f"VDB Add Law Failed: {e}")
        return CommonResponse(status="error")

if __name__ == "__main__":
    logger.info("--- RAG_APP 正在启动 ---")
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    logger.info("--- RAG_APP 启动完成 ---")
    logger.info(f"Using LLM_API_URL={LLM_API_URL}")

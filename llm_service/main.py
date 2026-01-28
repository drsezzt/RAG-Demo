from llm_service.engine import ChatGLM
from libs.protocols.llm_contract import GenerateResponse, GenerateRequest
from libs.utils.logger import init_component_logger
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = init_component_logger("LLM")
logger.info("RAG 推理服务启动...")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing model...")
    try:
        app.state.model = ChatGLM()
        logger.info("Model loaded into app state.")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise e
    yield

app = FastAPI(
    title="ChatGLM3-6B API",
    description="ChatGLM3-6B API",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {"msg": "ChatGLM3-6B API Service"}
@app.get("/health")
def check_health():
    return {"status": "healthy", "model_loaded": True}

@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
        model = app.state.model
        result, history = model.chat(**request.model_dump())
        return GenerateResponse(response=result, history=history)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=GenerateResponse(
            response="服务器内部错误",
            history=[],
            status="error",
        ).model_dump()
    )

if __name__ == "__main__":
    logger.info("Starting ChatGLM3-6B API server...")
    # 启动一个ASGI服务器
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )

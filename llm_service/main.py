"""
LLM service interface for RAG generation.
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from libs.settings import AppConfig
from libs.utils.logger import init_component_logger
from libs.protocols.llm_contract import GenerateResponse, GenerateRequest
from llm_service.engine import ChatGLM

logger = init_component_logger("LLM")
config = AppConfig.load("config/config.yaml")

REQUEST_ID_HEADER = "X-Request-ID"      # 请求ID
USER_ID_HEADER = "X-User-ID"            # 用户ID

async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get(REQUEST_ID_HEADER)
    if not req_id:
        req_id = uuid.uuid4().hex

    request.state.request_id = req_id

    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = req_id
    return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("op=llm_service_begin")

    models = config.llm.models
    if not models:
        raise Exception("No LLM models configured")

    logger.info(
        "op=app_set_model_start "
        f"usable_models={len(models)} "
        f"use_model={models[0].name}"
    )
    try:
        app.state.model = ChatGLM(models[0].path)
        logger.info("op=app_set_model_done")
    except Exception as e:
        logger.info("op=app_set_model_error")
        raise Exception("no models found")

    yield

    logger.info("op=llm_service_finish")

app = FastAPI(
    title="ChatGLM3-6B API",
    description="ChatGLM3-6B API",
    version="1.0.0",
    lifespan=lifespan
)
app.middleware("http")(request_id_middleware)

# 测试
@app.get("/")
def read_root():
    return {"msg": "ChatGLM3-6B API Service"}

# 测试
@app.get("/health")
def check_health(request: Request):
    logger.debug("op=health_check model_loaded=true")
    return {"status": "healthy", "model_loaded": True}

# 生成
@app.post("/generate", response_model=GenerateResponse)
def generate(
    request: Request,
    body: GenerateRequest
) -> GenerateResponse:
    req_id = request.state.request_id
    path = request.url.path
    user_id = (
        request.headers.get(USER_ID_HEADER)
        or body.user_id
        or "anonymous"
    )

    logger.info(
        "op=request_start "
        f"req={req_id} "
        f"user={user_id} "
        f"path={path}"
    )

    model = request.app.state.model

    try:
        result, history = model.chat(
            text=body.text,
            history=body.history,
            do_sample=body.do_sample,
            temperature=body.temperature,
            top_p=body.top_p,
            max_tokens=body.max_tokens,
            req_id=req_id,
            user_id=user_id,
        )

        response = GenerateResponse(
            response=result,
            history=history,
            status="ok"
        )

        logger.info(
            "op=request_end "
            f"req={req_id} "
            f"user={user_id} "
            f"path={path} "
            f"status=ok"
        )
        return response
    except Exception as e:
        logger.exception(
            "op=request_error "
            f"req={req_id} "
            f"user={user_id} "
            f"path={path} "
            f"error={type(e).__name__}"
        )
        raise

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "op=global_exception "
        f"error={type(exc).__name__}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content=GenerateResponse(
            response="服务器内部错误",
            history=[],
            status="error",
        ).model_dump()
    )

if __name__ == "__main__":
    # 启动一个ASGI服务器
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )

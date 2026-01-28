# 实现Pydantic模型

from pydantic import BaseModel

# 对话请求参数
class ChatRequest(BaseModel):
    text: str                       # 用户问题

# 对话响应参数
class ChatResponse(BaseModel):
    response: str                   # RAG回答

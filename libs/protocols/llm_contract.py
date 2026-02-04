# 实现Pydantic模型

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any

# 生成请求参数
class GenerateRequest(BaseModel):
    text: str                                           # 用户问题
    history: List[Dict[str, Any]] = Field(default_factory=list)     # 历史记录
    do_sample: bool = False                             # 是否开启采样
    temperature: float = Field(0.8, ge=0.0, le=2.0)     # 采样温度
    top_p: float = Field(0.9, ge=0.0, le=1.0)           # 采样阈值
    max_tokens: int = Field(512, ge=1, le=8192)         # 最大生成长度
    user_id: Optional[str] = None                       # 用户ID

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "什么是合同效力？",
                "history": [],
                "do_sample": False,
                "temperature": 0.8,
                "top_p": 0.9,
                "max_tokens": 512,
                "user_id": "user_123"
            }
        }
    }

# 生成响应参数
class GenerateResponse(BaseModel):
    response: str
    history: List[Dict[str, Any]]
    status: Literal["ok", "error"] = "ok"

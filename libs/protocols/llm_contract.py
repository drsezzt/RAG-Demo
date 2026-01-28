# 实现Pydantic模型

from pydantic import BaseModel

# 生成请求参数
class GenerateRequest(BaseModel):
    text: str                       # 用户问题
    history: list = []              # 历史记录
    do_sample: bool = False         # 是否开启采样
    temperature: float = 0.8        # 采样温度
    top_p: float = 0.9
    max_tokens: int = 512           # 最大生成长度

# 生成响应参数
class GenerateResponse(BaseModel):
    response: str
    history: list
    status: str = "success"

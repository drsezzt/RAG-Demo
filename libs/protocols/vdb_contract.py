# 实现Pydantic模型

from pydantic import BaseModel
from typing import Literal, List

# 获取文档列表响应参数
class GetDocListResponse(BaseModel):
    docs: List[dict] = []           # 支持的文档列表

# 添加文档请求参数
class AddDocRequest(BaseModel):
    name: str                       # 临时文件路径
    content: str                    # 临时文件路径

# 通用响应参数
class CommonResponse(BaseModel):
    status: Literal["ok", "error"] = "ok"

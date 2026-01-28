# 实现Pydantic模型

from pydantic import BaseModel
from typing import List

# 获取法律列表响应参数
class GetLawListResponse(BaseModel):
    laws: List[str] = []            # 支持的法律列表

# 添加法律请求参数
class AddLawRequest(BaseModel):
    name: str                       # 临时文件路径
    content: str                    # 临时文件路径

# 通用响应参数
class CommonResponse(BaseModel):
    status: str = "success"         # 状态
from typing import Protocol, List, Optional, runtime_checkable
import numpy as np


@runtime_checkable
class IVectorStore(Protocol):
    """向量存储接口"""
    def search(self, query_vector: np.ndarray, top_k: int) -> List[dict]:
        """向量搜索"""
        ...

    def add(self, metas: list, vectors: np.ndarray) -> bool:
        """添加向量"""
        ...

    def delete_by_file(self, file_id: str) -> bool:
        """按文件删除向量"""
        ...

    def get(self, chunk_id: int):
        """获取向量元数据"""
        ...

@runtime_checkable
class IMetadataRepository(Protocol):
    """元数据存储接口"""
    def add_file(self, meta) -> None:
        """添加文件元数据"""
        ...

    def get_file(self, file_id: str):
        """获取文件元数据"""
        ...

    def remove_file(self, file_id: str) -> None:
        """删除文件元数据"""
        ...

    def list_files(self) -> List:
        """列出所有文件"""
        ...

    def add_article(self, meta) -> None:
        """添加文章元数据"""
        ...

    def get_article(self, article_id: str):
        """获取文章元数据"""
        ...

    def remove_article(self, article_id: str) -> None:
        """删除文章元数据"""
        ...

@runtime_checkable
class IEmbedder(Protocol):
    """嵌入模型接口"""
    def embed_query(self, text: str) -> np.ndarray:
        """嵌入单个查询"""
        ...

    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        """嵌入多个文档"""
        ...

@runtime_checkable
class ILLMClient(Protocol):
    """LLM 客户端接口"""
    def chat(self, prompt: str, **kwargs) -> str:
        """发送聊天请求"""
        ...

@runtime_checkable
class IVectorStoreService(Protocol):
    """向量存储服务接口"""
    def search(self, query: str, top_k: int) -> List[dict]:
        """搜索文档"""
        ...

    def add_file(self, file_path: str) -> bool:
        """添加文件"""
        ...

    def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        ...

    def list_files(self) -> List:
        """列出文件"""
        ...
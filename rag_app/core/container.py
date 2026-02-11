from typing import Dict, Any
from rag_app.core.interface import (
    IVectorStore,
    IMetadataRepository,
    IEmbedder,
    ILLMClient,
    IVectorStoreService
)
from rag_app.vector_store.service import VectorStoreService

class DIContainer:
    """依赖注入容器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._services: Dict[str, Any] = {}

    def get_vector_store(self) -> IVectorStore:
        """获取向量存储实例"""
        if "vector_store" not in self._services:
            from rag_app.vector_store.raw_faiss.store import FaissVectorStore
            self._services["vector_store"] = FaissVectorStore(
                dim=self.config["vector_store"]["dimension"],
                store_dir=self.config["vector_store"]["index_path"]
            )
        return self._services["vector_store"]

    def get_metadata_repository(self) -> IMetadataRepository:
        """获取元数据存储实例"""
        if "metadata_repository" not in self._services:
            from rag_app.vector_store.metadata import MetadataRepository
            self._services["metadata_repository"] = MetadataRepository(
                path=self.config["vector_store"]["meta_path"]
            )
        return self._services["metadata_repository"]

    def get_embedder(self) -> IEmbedder:
        """获取嵌入模型实例"""
        if "embedder" not in self._services:
            from rag_app.libs.utils import get_embeddings
            self._services["embedder"] = get_embeddings()
        return self._services["embedder"]

    def get_llm_client(self) -> ILLMClient:
        """获取 LLM 客户端实例"""
        if "llm_client" not in self._services:
            from rag_app.core.llm_client import LLMClient
            url = f"http://{self.config['llm']['host']}:{self.config['llm']['port']}"
            self._services["llm_client"] = LLMClient(url)
        return self._services["llm_client"]

    def get_vector_store_service(self) -> IVectorStoreService:
        """获取向量存储服务实例"""
        if "vector_store_service" not in self._services:
            vector_store = self.get_vector_store()
            metadata_repo = self.get_metadata_repository()
            embedder = self.get_embedder()

            self._services["vector_store_service"] = VectorStoreService(
                store=vector_store,
                metadata=metadata_repo,
                embedder=embedder,
                embed_path=self.config["vector_store"]["embed_path"],
                chunk_size=self.config["vector_store"]["chunk_size"],
                chunk_overlap=self.config["vector_store"]["chunk_overlap"]
            )
        return self._services["vector_store_service"]

    def get_rag_service(self):
        """获取 RAG 服务实例"""
        if "rag_service" not in self._services:
            from rag_app.services.rag_service import RAGService
            llm_client = self.get_llm_client()
            vector_store_service = self.get_vector_store_service()

            self._services["rag_service"] = RAGService(
                llm_client=llm_client,
                vector_db=vector_store_service
            )
        return self._services["rag_service"]

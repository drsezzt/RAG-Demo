import os
import re
import uuid
import time
from typing import List
from datetime import datetime

import numpy as np

from rag_app.vector_store.raw_faiss.store import FaissVectorStore
from rag_app.vector_store.metadata import MetadataRepository
from rag_app.vector_store.types import FileMeta, ArticleMeta, ChunkMeta
from rag_app.vector_store.embedding_store import ArticleEmbeddingStore
from rag_app.core.interface import IVectorStoreService, IVectorStore, IMetadataRepository, IEmbedder
from shared.config import get_app_config, get_vdb_config
from libs.utils.logger import init_component_logger

logger = init_component_logger("VDB")

class VectorStoreService(IVectorStoreService):
    """
    向量库业务调度层
    """

    def __init__(
        self,
        store: IVectorStore,
        metadata: IMetadataRepository,
        embedder: IEmbedder,
        embed_path: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        """
        初始化向量存储服务

        Args:
            store: 向量存储接口
            metadata: 元数据存储接口
            embedder: 嵌入模型接口
            embed_path: 文章向量存储路径
            chunk_size: 文本切分大小（可选，默认从配置读取）
            chunk_overlap: 文本切分重叠（可选，默认从配置读取）
        """
        self.store = store
        self.metadata = metadata
        self.embedder = embedder
        self.embed_path = embed_path

        # 加载配置
        self.app_config = get_app_config()
        self.vdb_config = get_vdb_config()

        # 使用配置值或传入参数
        self.chunk_size = chunk_size if chunk_size is not None else self.vdb_config.chunk_size
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else self.vdb_config.chunk_overlap

        # 验证参数
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must < chunk_size")

        # 初始化文章向量存储
        self.article_store = ArticleEmbeddingStore(embed_path)

        logger.info(
            "VectorStoreService initialized with config: "
            f"chunk_size={self.chunk_size}, "
            f"chunk_overlap={self.chunk_overlap}, "
            f"embed_path={embed_path}"
        )

    # ===========================
    # Public API
    # ===========================

    def list_files(self) -> List[FileMeta]:
        """列出所有文件"""
        files_dict = self.metadata.list_all_files()
        return list(files_dict.values())

    def add_file(self, filename: str, content: str) -> bool:
        """
        添加文件到向量库

        Args:
            filename: 文件名
            content: 文件内容

        Returns:
            bool: 是否添加成功
        """
        start = time.time()

        # 1. 检查文件是否已存在
        for f in self.metadata.list_all_files().values():
            if f.filename == filename:
                raise ValueError(f"{filename} already indexed")

        # 2. 切分chunk和article
        chunks = self._split_text(content)

        # 3. Embedding
        vectors = self._embed(chunks)

        # 4. 生成 file_id
        file_id = str(uuid.uuid4().hex)

        # 5. 构造chunkmetas
        chunkmetas = []
        offset = 0
        for chunk in chunks:
            chunk_len = len(chunk)
            chunkmetas.append(ChunkMeta(
                file_id=file_id,
                offset=offset,
                length=chunk_len,
                text=chunk,
                created_at=datetime.now()
            ))
            offset += chunk_len

        # 6. 构造articlemetas
        articlemetas = []
        offset = 0
        articles = content.splitlines()
        article_ids = []
        for article in articles:
            article_id = str(uuid.uuid4().hex)
            article_ids.append(article_id)
            match = re.search(r'第[一二三四五六七八九十百千万零]+条', article)
            title = match.group() if match else "未知条款"
            article_len = len(article)
            articlemetas.append(ArticleMeta(
                article_id=article_id,
                file_id=file_id,
                title=title,
                offset=offset,
                length=article_len,
                text=article,
                created_at=datetime.now()
            ))
            offset += article_len

        # 7. chunk-article对齐
        self._align_chunks(chunkmetas, articlemetas)

        # 8. 写入向量库
        self.store.add(chunkmetas, vectors)

        # 9. 写 filemeta
        filemeta = FileMeta(
            file_id=file_id,
            filename=filename,
            chunks=len(chunks),
            size=len(content),
            article_ids=article_ids,
            created_at=datetime.now()
        )
        self.metadata.add_file(filemeta)

        # 10. 写 articlemeta 和文章向量
        for articlemate in articlemetas:
            self.metadata.add_article(articlemate)
            a_vec = self.embedder.embed_query(articlemate.text)
            self.article_store.save(articlemate.article_id, a_vec)

        logger.info(
            f"vdb_add_success file={filename} "
            f"chunks={len(chunks)} "
            f"time={time.time()-start:.2f}s"
        )
        return True

    def delete_file(self, file_id: str) -> bool:
        """
        删除文件

        Args:
            file_id: 文件ID

        Returns:
            bool: 是否删除成功
        """
        start = time.time()

        logger.info(f"vdb_delete_start file_id={file_id}")

        filemeta = self.metadata.get_file(file_id)

        if not filemeta:
            raise ValueError("file not found")

        # 1. 删除向量
        self.store.delete_by_file(file_id)

        # 2. 删除filemeta
        self.metadata.remove_file(file_id)

        # 3. 删除articlemeta
        artcle_ids = filemeta.article_ids
        for aid in artcle_ids:
            self.metadata.remove_article(aid)

        # 4. 删除embedding
        self.article_store.delete_batch(artcle_ids)

        logger.info(
            f"vdb_delete_success file={file_id} "
            f"time={time.time()-start:.2f}s"
        )
        return True

    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[dict]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            List[dict]: 搜索结果列表
        """
        logger.info(f"vdb_search_start k={top_k}")

        start = time.time()

        # 1. embedding
        q_vec = self._embed([query])[0]

        # 2. 搜索
        results = self.store.search(q_vec, top_k)

        logger.info(
            f"vdb_search_success hits={len(results)} "
            f"time={time.time()-start:.2f}s"
        )

        return results

    def get_chunk(self, chunk_id) -> ChunkMeta:
        return self.store.get(chunk_id)

    def embed_query(self, query: str) -> np.ndarray:
        return self.embedder.embed_query(query)

    def get_article_chunk(self, article_id: str):
        return self.article_store.get(article_id)

    def get_article_meta(self, article_id: str):
        return self.metadata.get_article(article_id)

    # ===========================
    # Internal Methods
    # ===========================

    def _split_text(self, text: str) -> List[str]:
        """
        切分文本

        Args:
            text: 原始文本

        Returns:
            List[str]: 切分后的文本块列表
        """
        chunks = []

        start = 0
        length = len(text)

        while start < length:
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap

        return chunks

    def _embed(self, texts: List[str]) -> np.ndarray:
        """
        文本向量化

        Args:
            texts: 文本列表

        Returns:
            np.ndarray: 向量数组
        """
        vectors = self.embedder.embed_documents(texts)
        return np.array(vectors, dtype="float32")

    def _align_chunks(self, chunkmetas: List[ChunkMeta], articlemetas: List[ArticleMeta]) -> None:
        """
        对齐chunk和article

        Args:
            chunkmetas: chunk元数据列表
            articlemetas: article元数据列表
        """
        for chunkmeta in chunkmetas:
            c_start, c_end = chunkmeta.offset, chunkmeta.offset + chunkmeta.length

            article_ids = []

            for articlemeta in articlemetas:
                a_start, a_end = articlemeta.offset, articlemeta.offset + articlemeta.length

                if not (c_end <= a_start or c_start >= a_end):
                    article_ids.append(articlemeta.article_id)

            chunkmeta.article_ids = article_ids
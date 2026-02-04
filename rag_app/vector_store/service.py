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
from libs.utils.logger import init_component_logger

logger = init_component_logger("VDB")

class VectorStoreService:
    """
    向量库业务调度层
    """

    def __init__(
        self,
        store: FaissVectorStore,
        metadata: MetadataRepository,
        embedder,
        embed_path,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.store = store
        self.metadata = metadata

        self.embedder = embedder
        self.embed_path = embed_path

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must < chunk_size")

    # ===========================
    # Public API
    # ===========================

    # ============ 保存章节的embedding ============
    def save_article_embeddings(self, article_id, vec):
        path = self.embed_path
        if os.path.exists(path):
            data = dict(np.load(path, allow_pickle=True))
        else:
            data = {}

        data[article_id] = np.asarray(vec, dtype=np.float32)

        np.savez_compressed(path, **data)

    def load_embeddings(self):
        path = self.embed_path
        if not os.path.exists(path):
            return {}

        data = np.load(path, allow_pickle=True)

        return {k: data[k] for k in data.files}

    def delete_embeddings(self, article_ids):
        data = self.load_embeddings()

        for aid in article_ids:
            data.pop(aid, None)

        np.savez_compressed(self.embed_path, **data)

    def list_files(self) -> List[FileMeta]:
        files_dict = self.metadata.list_all_files()
        return list(files_dict.values())

    def add_file(self, file_path: str):
        start = time.time()

        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        filename = os.path.basename(file_path)
        for f in self.metadata.list_all_files().values():
            if f.filename == filename:
                raise ValueError(f"{filename} already indexed")

        # 1. 读取文本
        text = self._load_file(file_path)

        # 2. 切分chunk和article
        chunks = self._split_text(text)

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
                created_at=datetime.now().isoformat()
            ))
            offset += chunk_len

        # 6. 构造articlemetas
        articlemetas = []
        offset = 0
        articles = text.splitlines()
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
                created_at=datetime.now().isoformat()
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
            size=os.path.getsize(file_path),
            article_ids=article_ids,
            created_at=datetime.now().isoformat()
        )
        self.metadata.add_file(filemeta)

        # 10. 写 articlemeta
        for articlemate in articlemetas:
            self.metadata.add_article(articlemate)
            a_vec = self.embedder.embed_query(articlemate.text)
            self.save_article_embeddings(articlemate.article_id, a_vec)

        logger.info(
            f"vdb_add_success file={filename} "
            f"chunks={len(chunks)} "
            f"time={time.time()-start:.2f}s"
        )
        return True

    def delete_file(self, file_id: str):

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
        self.delete_embeddings(artcle_ids)

        logger.info(
            f"vdb_delete_success file={file_id} "
            f"time={time.time()-start:.2f}s"
        )
        return True

    def search(
        self,
        query: str,
        top_k: int = 10
    ):
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

    # ===========================
    # Internal
    # ===========================

    def _load_file(self, path: str) -> str:

        ext = os.path.splitext(path)[1].lower()

        if ext in [".txt", ".md"]:

            with open(path, encoding="utf-8") as f:
                return f.read()

        raise ValueError(f"unsupported file: {ext}")

    def _split_text(self, text: str) -> List[str]:

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
        统一 embedding 入口
        """

        vectors = self.embedder.embed_documents(texts)

        return np.array(vectors, dtype="float32")

    def _align_chunks(self, chunkmetas: List[ChunkMeta], articlemetas: List[ArticleMeta]) -> List[str]:
        for chunkmeta in chunkmetas:
            c_start, c_end = chunkmeta.offset, chunkmeta.offset + chunkmeta.length

            article_ids = []

            for articlemeta in articlemetas:
                a_start, a_end = articlemeta.offset, articlemeta.offset + articlemeta.length

                if not (c_end <= a_start or c_start >= a_end):
                    article_ids.append(articlemeta.article_id)

            chunkmeta.article_ids = article_ids

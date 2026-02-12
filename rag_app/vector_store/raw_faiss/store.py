import os
import json
import faiss
import logging
import numpy as np
from datetime import datetime
import time as _time

from rag_app.vector_store.types import ChunkMeta, DocMap
from rag_app.core.interface import IVectorStore
from shared.config import get_vdb_config


logger = logging.getLogger("VDB")

class FaissVectorStore(IVectorStore):
    """
    FAISS 向量库存储层
    负责：
    - 向量存取
    - ID 映射
    - 持久化
    """

    def __init__(self):
        self.vdb_config = get_vdb_config()

        self.dim = self.vdb_config.dimension
        self.index_path = self.vdb_config.index_path
        self.map_path = self.vdb_config.map_path

        self.index = self._load_or_create_index()
        self.doc_map = self._load_or_create_map()

        # 如果 index / map 任一损坏或不一致，重置以保证可用性
        # （最小一致性：不因单文件损坏导致服务起不来）
        if getattr(self.index, "ntotal", None) is not None and self.index.ntotal != self.doc_map.next_id:
            logger.warning(
                "op=vdb_store_inconsistent_reset "
                f"index_ntotal={self.index.ntotal} "
                f"map_next_id={self.doc_map.next_id}"
            )
            self._reset()

    # ============ 加载向量库 ============
    def _load_or_create_index(self):
        if os.path.exists(self.index_path):
            try:
                return faiss.read_index(self.index_path)
            except Exception:
                # index 文件损坏：备份并重建
                try:
                    bak = self.index_path + f".corrupt.{int(_time.time())}"
                    os.replace(self.index_path, bak)
                    logger.exception(f"op=faiss_index_corrupt_backup path={bak}")
                except Exception:
                    logger.exception("op=faiss_index_corrupt_backup_failed")
                return faiss.IndexFlatIP(self.dim)

        print("🆕 Create new FAISS index")

        # 使用最基础版本，后期可换 IVF/HNSW
        index = faiss.IndexFlatIP(self.dim)     # 内积
        # index = faiss.IndexFlatL2(self.dim)     # L2距离

        return index

    # ============ 加载映射文件 ============
    def _load_or_create_map(self):
        if os.path.exists(self.map_path):
            try:
                with open(self.map_path, "r", encoding="utf-8") as f:
                    return DocMap.model_validate_json(f.read())
            except Exception:
                # JSON 截断/损坏：备份并重建（否则应用启动直接失败）
                try:
                    bak = self.map_path + f".corrupt.{int(_time.time())}"
                    os.replace(self.map_path, bak)
                    logger.exception(f"op=doc_map_corrupt_backup path={bak}")
                except Exception:
                    logger.exception("op=doc_map_corrupt_backup_failed")
                return DocMap()

        # 首次创建立即写盘
        doc_map = DocMap()
        with open(self.map_path, "w", encoding="utf-8") as f:
            json.dump(doc_map.model_dump(), f, indent=2, ensure_ascii=False)

        return doc_map

    # ============ 持久化向量库 ============
    def _save(self):
        # 先写临时文件再原子替换，避免崩溃导致文件截断
        tmp_index_path = self.index_path + ".tmp"
        faiss.write_index(self.index, tmp_index_path)
        os.replace(tmp_index_path, self.index_path)

        tmp_map_path = self.map_path + ".tmp"
        with open(tmp_map_path, "w", encoding="utf-8") as f:
            # 关键：使用 pydantic 的 JSON mode，确保 datetime 被序列化为字符串
            f.write(self.doc_map.model_dump_json(indent=2))
        os.replace(tmp_map_path, self.map_path)

    # ============ 归一化处理 ============
    def _normalize(self, vectors: np.ndarray):
        # 归一化，适合 inner product 搜索
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-12
        return vectors / norms

    def get(self, chunk_id: int) -> ChunkMeta:
        """
        获取向量
        """

        return self.doc_map.chunks.get(chunk_id)

    # ============ 添加向量 ============
    def add(
        self,
        metas: list[ChunkMeta],
        vectors: np.ndarray,
    ) -> bool:
        """
        添加向量

        vectors: (n, dim)
        """

        logger.info("op=chunk_add_start")
        if vectors.ndim != 2:
            raise ValueError("vectors must be 2D array")

        if vectors.shape[1] != self.dim:
            raise ValueError(f"dimension {vectors.shape[1]} mismatch {self.dim}")

        # 归一化处理
        vectors = self._normalize(vectors)

        count = vectors.shape[0]

        start_id = self.doc_map.next_id
        assert self.index.ntotal == start_id, "index size mismatch"

        ids = np.arange(start_id, start_id + count)
        self.index.add(vectors)

        # 建立映射
        for i in ids:
            chunk = metas[i - start_id]
            chunk.chunk_id = int(i)
            self.doc_map.chunks[int(i)] = chunk

        self.doc_map.next_id += count

        self._save()
        logger.info("op=chunk_add_done")
        return True

    # ============ 向量检索 ============
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10
    ) -> list[dict]:
        """
        查询

        return:
        [
            {
              file_id,
              score,
              chunk_id
            }
        ]
        """

        logger.info("op=chunk_search_start")
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        query_vector = self._normalize(query_vector)

        scores, ids = self.index.search(query_vector, top_k)

        results = []

        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue

            meta = self.doc_map.chunks.get(idx)
            if not meta:
                continue

            results.append({
                "file_id": meta.file_id,
                "score": float(score),
                "chunk_id": int(idx),
            })
        logger.info(
            "op=chunk_search_done "
            f"results_count={len(results)}"
        )

        return results

    # ============ 逻辑删除向量（重建索引） ============
    def delete_by_file(
        self,
        file_id: str
    ) -> bool:
        """
        根据 file_id 删除
        FAISS 不支持物理删除 → 重建索引
        """

        logger.info(
            "op=chunk_delete_start "
            f"file_id={file_id}"
        )

        keep_ids = []
        for cid, meta in self.doc_map.chunks.items():
            if meta.file_id != file_id:
                keep_ids.append(cid)

        if not keep_ids:
            logger.warning("⚠️ No vectors to keep, reset index")
            self._reset()
            logger.info("op=chunk_del_empty")
            return True

        keep_ids = np.array(keep_ids)

        # 全量拷贝，可能存在性能隐患，需要优化
        vectors = self.index.reconstruct_n(0, self.index.ntotal)
        keep_vectors = vectors[keep_ids]

        # 重建索引
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(keep_vectors)

        # 重建 map
        new_chunks = {}
        for new_id, old_id in enumerate(keep_ids):
            meta = self.doc_map.chunks[old_id]
            meta.chunk_id = new_id
            new_chunks[new_id] = meta

        self.doc_map = DocMap(
            next_id=len(keep_ids),
            chunks=new_chunks
        )

        self._save()
        logger.info("op=chunk_delete_done")
        return True

    # ============ 获取向量库信息 ============
    def info(self):
        return {
            "total_vectors": self.index.ntotal,
            "total_files": len(set(self.doc_map.chunks.values())),
        }

    # ============ 重置向量库 ============
    def _reset(self):
        self.index = faiss.IndexFlatIP(self.dim)

        self.doc_map = DocMap()

        self._save()

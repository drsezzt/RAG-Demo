import os
import threading
import numpy as np
import logging


logger = logging.getLogger("VDB")


class ArticleEmbeddingStore:
    """
    Article Embedding 本地存储（NPZ）

    职责：
    - article_id -> embedding 映射
    - 持久化
    - 删除

    ⚠️ 当前为单机轻量方案，后期可替换为 DB / KV / Milvus
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()

    # ======================
    # Internal
    # ======================

    def _load_all(self) -> dict:
        """
        读取全部 embedding
        """

        if not os.path.exists(self.path):
            return {}

        data = np.load(self.path, allow_pickle=True)

        return {
            k: data[k]
            for k in data.files
        }

    def _save_all(self, data: dict):
        """
        全量写回
        """

        tmp_path = self.path + ".tmp.npz"

        np.savez_compressed(tmp_path, **data)

        # 原子替换，防止写一半崩溃
        os.replace(tmp_path, self.path)

    # ======================
    # Public API
    # ======================

    def get(self, article_id: str):
        """
        获取单个 embedding
        """

        data = self._load_all()

        return data.get(article_id)

    def get_batch(self, article_ids: list[str]) -> dict:
        """
        批量获取
        """

        data = self._load_all()

        result = {}

        for aid in article_ids:
            if aid in data:
                result[aid] = data[aid]

        return result

    def save(self, article_id: str, embedding: np.ndarray):
        """
        保存单条 embedding
        """

        with self._lock:

            data = self._load_all()

            data[article_id] = np.asarray(
                embedding,
                dtype=np.float32
            )

            self._save_all(data)

        logger.debug(f"article_embedding_saved id={article_id}")

    def save_batch(self, items: dict):
        """
        批量保存

        items:
        {
            article_id: embedding
        }
        """

        with self._lock:

            data = self._load_all()

            for aid, vec in items.items():
                data[aid] = np.asarray(vec, dtype=np.float32)

            self._save_all(data)

        logger.debug(f"article_embedding_saved_batch size={len(items)}")

    def delete(self, article_id: str):
        """
        删除单条
        """

        with self._lock:

            data = self._load_all()

            if article_id in data:
                del data[article_id]

                self._save_all(data)

        logger.debug(f"article_embedding_deleted id={article_id}")

    def delete_batch(self, article_ids: list[str]):
        """
        批量删除
        """

        with self._lock:

            data = self._load_all()

            for aid in article_ids:
                data.pop(aid, None)

            self._save_all(data)

        logger.debug(
            f"article_embedding_deleted_batch size={len(article_ids)}"
        )

    def exists(self, article_id: str) -> bool:
        """
        是否存在
        """

        data = self._load_all()

        return article_id in data

    def count(self) -> int:
        """
        总数量
        """

        data = self._load_all()

        return len(data)

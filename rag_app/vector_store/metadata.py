import os
import json
import logging

from typing import Optional, Dict

from rag_app.vector_store.types import FileMeta, ArticleMeta, MetadataSchema
from rag_app.core.interface import IMetadataRepository


logger = logging.getLogger("VDB")

class MetadataRepository(IMetadataRepository):
    def __init__(self, path: str):
        self.path = path
        self._store = self._load_or_init()

    # =====================
    # Init
    # =====================

    def _load_or_init(self) -> MetadataSchema:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return MetadataSchema.model_validate_json(f.read())

        data = MetadataSchema()
        self._save(data)

        return data

    def _save(self, data: Optional[MetadataSchema] = None):
        if not data:
            data = self._store

        with open(self.path, "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=2))

    # =====================
    # CRUD
    # =====================

    def add_file(self, meta: FileMeta):
        logger.info("op=meta_add_file_start")

        self._store.files[meta.file_id] = meta
        self._save()

        logger.info("op=meta_add_file_done")

    def add_article(self, meta: ArticleMeta):
        logger.info("op=meta_add_article_start")

        self._store.articles[meta.article_id] = meta
        self._save()

        logger.info("op=meta_add_article_done")

    def get_file(self, file_id: str) -> Optional[FileMeta]:
        logger.info(f"op=meta_get_file file_id={file_id}")
        return self._store.files.get(file_id)

    def get_article(self, article_id: str) -> Optional[ArticleMeta]:
        logger.info(f"op=meta_get_article article_id={article_id}")
        return self._store.articles.get(article_id)

    def remove_file(self, file_id: str):
        logger.info(f"op=meta_remove_file_start file_id={file_id}")

        if file_id in self._store.files:
            del self._store.files[file_id]
            self._save()

        logger.info("op=meta_remove_file_done")

    def remove_article(self, article_id: str):
        logger.info(f"op=meta_remove_article_start article_id={article_id}")

        if article_id in self._store.articles:
            del self._store.articles[article_id]
            self._save()

        logger.info("op=meta_remove_article_done")

    def file_exists(self, file_id: str) -> bool:
        return file_id in self._store.files

    def article_exists(self, article_id: str) -> bool:
        return article_id in self._store.articles

    def list_all_files(self) -> Dict[str, FileMeta]:
        logger.info("op=meta_list_files_start")
        result = {}

        for name, data in self._store.files.items():
            result[name] = FileMeta.model_validate(data)

        logger.info("op=meta_list_files_done")
        return result

    def list_all_articles(self) -> Dict[str, ArticleMeta]:
        logger.info("op=meta_list_articles_start")
        result = {}

        for name, data in self._store.articles.items():
            result[name] = ArticleMeta.model_validate(data)

        logger.info("op=meta_list_articles_done")
        return result

    def list_articles_by_file(self, file_id: str) -> list[ArticleMeta]:
        logger.info("op=meta_list_articles_start")

        result = []
        for name, data in self._store.articles.items():
            if data["file_id"] == file_id:
                result.append(ArticleMeta.model_validate(data))

        logger.info("op=meta_list_articles_done")
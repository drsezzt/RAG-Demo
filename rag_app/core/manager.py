from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import logging
import os
import re

logger = logging.getLogger("RAG_APP")

class VectorManager:
    def __init__(self, vdb_path, embeddings):
        self.vdb_path = vdb_path
        self.embeddings = embeddings
        self._vdb = None

    @property
    def vdb(self):
        """显式初始化逻辑"""
        if self._vdb is None:
            # 情况 A: 磁盘已有库，直接加载
            if os.path.exists(self.vdb_path):
                try:
                    self._vdb = FAISS.load_local(
                        self.vdb_path,
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    return self._vdb
                except Exception as e:
                    raise Exception(f"Failed to load vector database: {str(e)}")

        return self._vdb

    def get_supported_laws(self):
        if not self.vdb:
            return []

        """获取法律列表"""
        all_docs = self.vdb.docstore._dict.values()
        laws = {doc.metadata.get("law_name") for doc in all_docs if doc.metadata.get("law_name")}
        return sorted(list(laws))

    def delete_law(self, law_name):
        """删除法律：过滤并重建索引"""
        if not self.vdb:
            return False

        all_docs = list(self.vdb.docstore._dict.values())
        remaining_docs = [doc for doc in all_docs if doc.metadata.get("law_name") != law_name]

        if remaining_docs:
            self._vdb = FAISS.from_documents(remaining_docs, self.embeddings)
            self._vdb.save_local(self.vdb_path)
        else:
            import shutil
            if os.path.exists(self.vdb_path):
                shutil.rmtree(self.vdb_path)
            self._vdb = None

        return True

    def add_new_law(self, law_name, full_text):
        line_docs = []
        lines = full_text.splitlines()
        for line in lines:
            line = line.strip()
            if not line: continue

            match = re.search(r'第[一二三四五六七八九十百]+条', line)
            if not match: continue
            article_name = match.group(0)
            clean_content = line.split("规定，")[-1] if "规定，" in line else line
            new_doc = Document(
                page_content=f"{article_name}：{clean_content}",
                metadata={
                    "law_name": law_name,
                    "article_name": article_name
                }
            )
            line_docs.append(new_doc)

        """增量合并新法律"""
        if os.path.exists(self.vdb_path):
            self.vdb.add_documents(line_docs)
            self.vdb.save_local(self.vdb_path)
        else:
            # 库不存在则新建
            new_vdb = FAISS.from_documents(line_docs, self.embeddings)
            new_vdb.save_local(self.vdb_path)
            self._vdb = new_vdb

        return True

import os
from langchain_huggingface import HuggingFaceEmbeddings

# 使用全局变量实现单例模式
_embeddings_instance = None

def get_embeddings():
    global _embeddings_instance
    if _embeddings_instance is None:
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        bge_path = os.path.join(curr_dir, "..", "bge-small-zh-v1.5")

        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=bge_path,
            model_kwargs={"device": 'cpu'},
            encode_kwargs={"normalize_embeddings": True},
        )

    return _embeddings_instance

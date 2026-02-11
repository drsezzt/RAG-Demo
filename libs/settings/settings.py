from pydantic import BaseModel
from pydantic_settings import BaseSettings
import yaml

class ModelConfig(BaseModel):
    name: str
    path: str

class LLMConfig(BaseModel):
    host: str
    port: int
    models: list[ModelConfig]

class RAGConfig(BaseModel):
    host: str
    port: int

class VectorStoreConfig(BaseModel):
    index_path: str
    meta_path: str
    map_path: str
    embed_path: str
    dimension: int
    chunk_size: int
    chunk_overlap: int

class UIConfig(BaseModel):
    host: str
    rag_port: int
    vdb_port: int

class AppConfig(BaseSettings):
    env: str = "local"
    llm: LLMConfig
    rag: RAGConfig
    vector_store: VectorStoreConfig
    ui: UIConfig

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

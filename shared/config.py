"""
统一配置管理系统
基于类型安全的专用配置类设计
"""
import os
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator, BaseModel


class ModelConfig(BaseModel):
    """模型配置"""
    name: str = Field(..., description="模型名称")
    path: str = Field(..., description="模型文件路径")


# ==================== 组件配置类 ====================

class ComponentConfig(BaseSettings):
    """组件配置基类"""
    pass


class LLMConfig(ComponentConfig):
    """LLM 服务专用配置"""

    host: str = Field("0.0.0.0", description="LLM 服务主机")
    port: int = Field(8001, description="LLM 服务端口")
    endpoint: str = Field("/generate", description="LLM 服务端点")

    # 模型配置
    models: List[ModelConfig] = Field(
        default_factory=lambda: [
            ModelConfig(
                name="ChatGLM3-6B-Q5_1",
                path="/home/zzt/models/llm/chatglm3/6b-q5_1/chatglm3-q5_1.bin"
            )
        ],
        description="LLM 模型列表"
    )

    # 请求配置
    max_retries: int = Field(3, description="最大重试次数")
    retry_delay: float = Field(1.0, description="重试延迟（秒）")

    # 模型参数
    default_temperature: float = Field(0.01, description="温度参数")
    default_top_p: float = Field(0.1, description="top_p 参数")
    default_max_tokens: int = Field(8192, description="最大token数")

    class Config:
        env_prefix = "LLM_"


class RAGConfig(ComponentConfig):
    """RAG 服务专用配置"""

    host: str = Field("0.0.0.0", description="RAG 服务主机")
    port: int = Field(8000, description="RAG 服务端口")
    endpoint: str = Field("/chat", description="RAG 服务端点")

    # 请求配置
    timeout: int = Field(60, description="请求超时时间（秒）")

    # 检索配置
    similarity_threshold: float = Field(0.65, description="相似度阈值")
    top_k_retrieval: int = Field(10, description="检索返回数量")
    max_retrieved_articles: int = Field(2, description="最大返回文章数")

    # 生成参数
    chat_temperature: float = Field(0.01, description="聊天温度参数")
    chat_top_p: float = Field(0.1, description="聊天top_p参数")
    chat_max_tokens: int = Field(8192, description="聊天最大token数")

    @validator("similarity_threshold")
    def validate_similarity_threshold(cls, v):
        """验证相似度阈值在合理范围内"""
        if not 0 <= v <= 1:
            raise ValueError("similarity_threshold 必须在 0 到 1 之间")
        return v

    class Config:
        env_prefix = "RAG_"


class VectorStoreConfig(ComponentConfig):
    """向量存储专用配置"""

    type: str = Field("faiss", description="向量存储类型")
    dimension: int = Field(512, description="向量维度")

    # 路径配置
    index_path: str = Field("data/vector_store/faiss.index", description="索引路径")
    meta_path: str = Field("data/vector_store/metadata.json", description="元数据路径")
    map_path: str = Field("data/vector_store/doc_map.json", description="映射路径")
    embed_path: str = Field("data/vector_store/article_embeddings.npz", description="向量路径")

    # 文本处理配置
    chunk_size: int = Field(500, description="文本切分大小")
    chunk_overlap: int = Field(50, description="文本切分重叠")

    @validator("chunk_overlap")
    def validate_chunk_overlap(cls, v, values):
        """验证 chunk_overlap 小于 chunk_size"""
        if "chunk_size" in values and v >= values["chunk_size"]:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        return v

    class Config:
        env_prefix = "VECTOR_STORE_"


class UIConfig(ComponentConfig):
    """UI 服务专用配置"""

    # 请求配置
    timeout: int = Field(60, description="请求超时时间（秒）")

    class Config:
        env_prefix = "UI_"


# ==================== 应用配置类 ====================

class AppConfig(BaseSettings):
    """应用配置（合并全局和共享配置）"""

    # 全局超时时间
    timeout: int = Field(60, description="请求超时时间（秒）")

    # 应用元数据
    app_name: str = Field("RAGSystem", description="应用名称")
    app_description: str = Field("RAGSystem API", description="应用描述")
    app_version: str = Field("1.0.0", description="应用版本")
    environment: str = Field("development", description="运行环境")

    # 运行时配置
    log_level: str = Field("INFO", description="日志级别")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )

    # 文件处理配置
    supported_file_extensions: List[str] = Field(
        [".txt", ".md"],
        description="支持的文件扩展名"
    )
    max_file_size_mb: int = Field(10, description="最大文件大小（MB）")

    class Config:
        env_file = ".env"
        env_prefix = "RAG_"
        case_sensitive = False


# ==================== 配置加载器 ====================

class ConfigLoader:
    """统一配置加载器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            config_path: 配置文件路径，如果为 None 则使用默认加载方式
        """
        # 初始化各配置类
        self.app_config = AppConfig()
        self.llm_config = LLMConfig()
        self.rag_config = RAGConfig()
        self.vdb_config = VectorStoreConfig()
        self.ui_config = UIConfig()

        # 加载配置文件（如果存在）
        if config_path:
            self._load_from_file(config_path)

    def _load_from_file(self, path: str):
        """
        从配置文件加载配置

        Args:
            path: 配置文件路径
        """
        if not os.path.exists(path):
            return

        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        if not config_data:
            return

        # 转换配置格式并更新各配置类
        self._update_configs_from_dict(config_data)

    def _update_configs_from_dict(self, config_data: Dict[str, Any]):
        """
        从字典更新各配置类

        Args:
            config_data: 配置数据字典
        """
        # 更新应用配置
        app_data = self._extract_app_config(config_data)
        if app_data:
            self.app_config = AppConfig(**app_data)

        # 更新 LLM 配置
        llm_data = self._extract_llm_config(config_data)
        if llm_data:
            self.llm_config = LLMConfig(**llm_data)

        # 更新 RAG 配置
        rag_data = self._extract_rag_config(config_data)
        if rag_data:
            self.rag_config = RAGConfig(**rag_data)

        # 更新向量存储配置
        vector_data = self._extract_vdb_config(config_data)
        if vector_data:
            self.vdb_config = VectorStoreConfig(**vector_data)

        # 更新 UI 配置
        ui_data = self._extract_ui_config(config_data)
        if ui_data:
            self.ui_config = UIConfig(**ui_data)

    def _extract_app_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取应用配置数据"""
        result = {}

        # 环境配置
        if "env" in config_data:
            result["environment"] = config_data["env"]

        # 其他应用配置可以在这里添加
        return result

    def _extract_llm_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取 LLM 配置数据"""
        result = {}

        if "llm" in config_data:
            llm = config_data["llm"]

            # 基本配置
            if "host" in llm:
                result["host"] = llm["host"]
            if "port" in llm:
                result["port"] = llm["port"]

            # 模型配置
            if "models" in llm:
                result["models"] = [
                    ModelConfig(name=model.get("name", ""), path=model.get("path", ""))
                    for model in llm["models"]
                ]

        return result

    def _extract_rag_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取 RAG 配置数据"""
        result = {}

        if "rag" in config_data:
            rag = config_data["rag"]

            if "host" in rag:
                result["host"] = rag["host"]
            if "port" in rag:
                result["port"] = rag["port"]

        return result

    def _extract_vdb_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取向量存储配置数据"""
        result = {}

        if "vector_store" in config_data:
            vs = config_data["vector_store"]

            # 路径配置
            if "index_path" in vs:
                result["index_path"] = vs["index_path"]
            if "meta_path" in vs:
                result["meta_path"] = vs["meta_path"]
            if "map_path" in vs:
                result["map_path"] = vs["map_path"]
            if "embed_path" in vs:
                result["embed_path"] = vs["embed_path"]

            # 维度配置
            if "dimension" in vs:
                result["dimension"] = vs["dimension"]

            # 文本处理配置
            if "chunk_size" in vs:
                result["chunk_size"] = vs["chunk_size"]
            if "chunk_overlap" in vs:
                result["chunk_overlap"] = vs["chunk_overlap"]

        return result

    def _extract_ui_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取 UI 配置数据"""
        result = {}

        if "ui" in config_data:
            ui = config_data["ui"]

            if "host" in ui:
                result["host"] = ui["host"]
            if "rag_port" in ui:
                result["rag_port"] = ui["rag_port"]
            if "vdb_port" in ui:
                result["vdb_port"] = ui["vdb_port"]

        return result

    # 获取方法
    def get_app_config(self) -> AppConfig:
        """获取应用配置"""
        return self.app_config

    def get_llm_config(self) -> LLMConfig:
        """获取 LLM 配置"""
        return self.llm_config

    def get_rag_config(self) -> RAGConfig:
        """获取 RAG 配置"""
        return self.rag_config

    def get_vdb_config(self) -> VectorStoreConfig:
        """获取向量存储配置"""
        return self.vdb_config

    def get_ui_config(self) -> UIConfig:
        """获取 UI 配置"""
        return self.ui_config


# ==================== 全局单例 ====================

_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_path: Optional[str] = None) -> ConfigLoader:
    """
    获取配置加载器实例（单例）

    Args:
        config_path: 配置文件路径

    Returns:
        ConfigLoader: 配置加载器实例
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def get_app_config() -> AppConfig:
    """获取应用配置"""
    return get_config_loader().get_app_config()


def get_llm_config() -> LLMConfig:
    """获取 LLM 配置"""
    return get_config_loader().get_llm_config()


def get_rag_config() -> RAGConfig:
    """获取 RAG 配置"""
    return get_config_loader().get_rag_config()


def get_vdb_config() -> VectorStoreConfig:
    """获取向量存储配置"""
    return get_config_loader().get_vdb_config()


def get_ui_config() -> UIConfig:
    """获取 UI 配置"""
    return get_config_loader().get_ui_config()


def reset_config():
    """重置配置（主要用于测试）"""
    global _config_loader
    _config_loader = None
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class ChunkMeta(BaseModel):
    """
    文本分块元信息
    """

    chunk_id: int = 0
    file_id: str

    article_ids: list[str] = Field(default_factory=list)

    offset: int = Field(ge=0)
    length: int = Field(gt=0)

    created_at: Optional[datetime] = None

    text: str


class DocMap(BaseModel):
    """
    Chunk 映射表
    """

    next_id: int = 0

    chunks: dict[int, ChunkMeta] = Field(default_factory=dict)


class ArticleMeta(BaseModel):
    """
    章节信息
    """

    article_id: str
    file_id: str

    title: Optional[str] = None

    offset: int = Field(ge=0)
    length: int = Field(gt=0)

    created_at: Optional[datetime] = None

    text: str


class FileMeta(BaseModel):
    """
    文件元信息
    """

    file_id: str
    filename: str

    chunks: int = Field(gt=0)
    size: int = Field(gt=0)

    article_ids: list[str] = Field(default_factory=list)

    created_at: Optional[datetime] = None

class MetadataSchema(BaseModel):
    files: dict[str, FileMeta] = Field(default_factory=dict)
    articles: dict[str, ArticleMeta] = Field(default_factory=dict)
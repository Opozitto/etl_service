from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.document import StructuredDocument


class ProcessResponse(BaseModel):
    document: StructuredDocument


class DocumentListItem(BaseModel):
    document_id: str
    title: str
    filename: str
    processed_at: str
    page_count: Optional[int] = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchHit(BaseModel):
    document_id: str
    title: str
    filename: str
    score: float
    chunk_id: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    snippet: str


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)
    max_sentences: int = Field(default=4, ge=1, le=8)


class AskResponse(BaseModel):
    question: str
    answer: str
    hits: list[SearchHit]
    strategy: str


class CorpusStatsResponse(BaseModel):
    document_count: int
    chunk_count: int
    avg_chunk_length: float
    updated_at: str
    manifest_record_count: int


class ReindexResponse(BaseModel):
    status: str
    document_count: int
    chunk_count: int
    updated_at: str


class ManifestRecordResponse(BaseModel):
    document_id: str
    filename: str
    checksum_sha256: str
    title: str
    extension: str
    extractor: str
    status: str
    processed_at: str
    warnings: list[str]
    source_encoding: Optional[str] = None

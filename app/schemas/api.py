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


class AskSource(BaseModel):
    rank: int
    score: float
    document_id: str
    filename: str
    title: str
    chunk_id: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    snippet: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[AskSource]
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


class RequirementCandidateResponse(BaseModel):
    document_id: str
    filename: str
    category: str
    score: float
    source_type: str
    block_id: Optional[str] = None
    chunk_id: Optional[str] = None
    table_id: Optional[str] = None
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    page: Optional[int] = None
    matched_terms: list[str]
    reason_codes: list[str]
    text: str
    snippet: str


class RequirementsSummaryResponse(BaseModel):
    documents_seen: int
    documents_with_candidates: int
    total_candidates: int
    categories: dict[str, int]


class RequirementsResponse(BaseModel):
    report_version: str
    stage: str
    scope_note: str
    results_dir: str
    summary: RequirementsSummaryResponse
    candidates: list[RequirementCandidateResponse]


class TableEvidenceCandidateResponse(BaseModel):
    document_id: str
    filename: str
    table_id: Optional[str] = None
    block_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_type: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    page: Optional[int] = None
    row_count: int
    column_count: int
    headers: list[str]
    detected_columns: list[str]
    preview_rows: list[list[str]]
    category: str
    tags: list[str]
    score: float
    matched_terms: list[str]
    reason_codes: list[str]
    snippet: str
    text_preview: str


class TableEvidenceSummaryResponse(BaseModel):
    documents_seen: int
    documents_with_tables: int
    tables_seen: int
    candidate_tables: int
    categories: dict[str, int]


class TableEvidenceResponse(BaseModel):
    report_version: str
    stage: str
    scope_note: str
    results_dir: str
    summary: TableEvidenceSummaryResponse
    tables: list[TableEvidenceCandidateResponse]

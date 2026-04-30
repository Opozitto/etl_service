from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


BlockType = Literal["heading", "paragraph", "list_item", "table", "image", "text"]


class SourceInfo(BaseModel):
    filename: str
    extension: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum_sha256: str
    saved_path: Optional[str] = None


class DocumentMetadata(BaseModel):
    document_id: str
    title: str
    language: Optional[str] = "ru"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    page_count: Optional[int] = None
    section_count: int = 0
    block_count: int = 0
    table_count: int = 0
    image_count: int = 0


class Section(BaseModel):
    section_id: str
    title: str
    level: int
    parent_id: Optional[str] = None
    order: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    block_ids: list[str] = Field(default_factory=list)


class Block(BaseModel):
    block_id: str
    type: BlockType
    order: int
    text: Optional[str] = None
    section_id: Optional[str] = None
    page_num: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TableCell(BaseModel):
    row: int
    column: int
    value: str


class TableData(BaseModel):
    table_id: str
    order: int
    section_id: Optional[str] = None
    page_num: Optional[int] = None
    n_rows: int
    n_cols: int
    rows: list[list[str]] = Field(default_factory=list)
    cells: list[TableCell] = Field(default_factory=list)


class ImageInfo(BaseModel):
    image_id: str
    order: int
    page_num: Optional[int] = None
    section_id: Optional[str] = None
    caption: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    section_id: Optional[str] = None
    block_ids: list[str] = Field(default_factory=list)
    content_type: Optional[str] = None
    source_type: Optional[str] = None
    section_title: Optional[str] = None
    section_path: list[str] = Field(default_factory=list)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    source_filename: Optional[str] = None
    table_id: Optional[str] = None
    table_title: Optional[str] = None
    table_headers: list[str] = Field(default_factory=list)
    table_row_index: Optional[int] = None
    table_column_values: dict[str, str] = Field(default_factory=dict)
    table_context: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    text: str
    order: int
    token_estimate: int


class ProcessingInfo(BaseModel):
    extractor: str
    transform_version: str = "baseline-v1"
    warnings: list[str] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)
    ocr_candidate: bool = False
    ocr_reason: Optional[str] = None
    source_encoding: Optional[str] = None
    text_char_count: int = 0
    text_block_count: int = 0
    extractor_metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentArtifact(BaseModel):
    result_json_path: str
    source_file_path: Optional[str] = None


class StructuredDocument(BaseModel):
    metadata: DocumentMetadata
    source: SourceInfo
    sections: list[Section] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    tables: list[TableData] = Field(default_factory=list)
    images: list[ImageInfo] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    processing_info: ProcessingInfo
    artifacts: DocumentArtifact

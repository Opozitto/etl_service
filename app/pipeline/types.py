from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


RawBlockType = Literal["text", "heading", "paragraph", "list_item", "table", "image"]


@dataclass
class RawBlock:
    kind: RawBlockType
    text: Optional[str] = None
    page_num: Optional[int] = None
    style_hint: Optional[str] = None
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedDocument:
    extractor_name: str
    text: str
    blocks: list[RawBlock]
    page_count: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

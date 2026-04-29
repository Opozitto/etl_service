from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.pipeline.types import ExtractedDocument


class BaseExtractor(ABC):
    supported_extensions: tuple[str, ...] = ()
    name: str = "base"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def extract(self, path: Path) -> ExtractedDocument:
        raise NotImplementedError


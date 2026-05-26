from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "ETL Service"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    project_root: Path = Path(__file__).resolve().parents[2]
    storage_dir: Path = Field(default_factory=lambda: Path("storage"))
    uploads_dir_name: str = "uploads"
    results_dir_name: str = "results"
    index_dir_name: str = "index"
    default_chunk_size: int = 900
    default_chunk_overlap: int = 150
    enable_ocr: bool = False
    rules_config_path: Path | None = None

    @property
    def resolved_storage_dir(self) -> Path:
        if self.storage_dir.is_absolute():
            return self.storage_dir
        return (self.project_root / self.storage_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    storage_dir = os.getenv("ETL_STORAGE_DIR", "storage")
    enable_ocr = os.getenv("ETL_ENABLE_OCR", "false").strip().lower() in {"1", "true", "yes", "on"}
    api_prefix = os.getenv("ETL_API_PREFIX", "/api/v1")
    rules_config_path = os.getenv("ETL_RULES_CONFIG_PATH", "").strip()
    return Settings(
        storage_dir=Path(storage_dir),
        enable_ocr=enable_ocr,
        api_prefix=api_prefix,
        rules_config_path=Path(rules_config_path) if rules_config_path else None,
    )

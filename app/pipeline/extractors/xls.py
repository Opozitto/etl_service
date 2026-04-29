from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import is_zipfile

from app.pipeline.errors import ExtractionError
from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.types import ExtractedDocument, RawBlock


class XlsExtractor(BaseExtractor):
    supported_extensions = (".xls",)
    name = "xls"

    def extract(self, path: Path) -> ExtractedDocument:
        if is_zipfile(path):
            return self._extract_xlsx_container(path)

        try:
            import xlrd
            from xlrd import XLRDError
            from xlrd.xldate import xldate_as_datetime
        except ImportError as exc:  # pragma: no cover - dependency wiring
            raise ExtractionError("XLS support requires the xlrd dependency", code="missing_dependency") from exc

        try:
            workbook = xlrd.open_workbook(str(path))
        except XLRDError as exc:
            raise ExtractionError(f"Failed to read {path.name} as XLS: {exc}", code="extract_failed") from exc
        except Exception as exc:  # pragma: no cover - defensive wrapping
            raise ExtractionError(f"Failed to read {path.name} as XLS: {exc}", code="extract_failed") from exc

        blocks: list[RawBlock] = []
        text_parts: list[str] = []
        sheet_count = 0

        for sheet in workbook.sheets():
            rows = self._read_sheet_rows(sheet, workbook.datemode, xldate_as_datetime)
            if not rows:
                continue

            sheet_count += 1
            blocks.append(RawBlock(kind="heading", text=sheet.name, metadata={"sheet_name": sheet.name}))
            table_text = "\n".join(" | ".join(row) for row in rows)
            blocks.append(
                RawBlock(
                    kind="table",
                    text=table_text,
                    data=rows,
                    metadata={"sheet_name": sheet.name},
                )
            )
            text_parts.append(f"Sheet: {sheet.name}")
            text_parts.extend(" | ".join(row) for row in rows)

        return ExtractedDocument(
            extractor_name=self.name,
            text="\n".join(text_parts),
            blocks=blocks,
            metadata={"sheet_count": sheet_count, "workbook_name": path.name},
        )

    def _extract_xlsx_container(self, path: Path) -> ExtractedDocument:
        from app.pipeline.extractors.xlsx import XlsxExtractor

        extracted = XlsxExtractor().extract(path)
        extracted.extractor_name = self.name
        extracted.metadata = {
            **extracted.metadata,
            "workbook_name": path.name,
            "detected_container": "zip",
        }
        return extracted

    def _read_sheet_rows(self, sheet, datemode: int, xldate_as_datetime) -> list[list[str]]:
        rows: list[list[str]] = []
        for row_idx in range(sheet.nrows):
            values = [self._cell_value(sheet, row_idx, col_idx, datemode, xldate_as_datetime) for col_idx in range(sheet.ncols)]
            while values and values[-1] == "":
                values.pop()
            if any(values):
                rows.append(values)
        return rows

    def _cell_value(self, sheet, row_idx: int, col_idx: int, datemode: int, xldate_as_datetime) -> str:
        cell = sheet.cell(row_idx, col_idx)
        value = cell.value

        if cell.ctype == 0:
            return ""
        if cell.ctype == 1:
            return str(value).strip()
        if cell.ctype == 2:
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value).strip()
        if cell.ctype == 3:
            try:
                dt = xldate_as_datetime(value, datemode)
            except Exception:
                return str(value).strip()
            return _format_datetime(dt)
        if cell.ctype == 4:
            return "TRUE" if bool(value) else "FALSE"
        if cell.ctype == 5:
            return ""
        return str(value).strip()


def _format_datetime(value: datetime) -> str:
    if value.time() == datetime.min.time():
        return value.date().isoformat()
    return value.isoformat(sep=" ")

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.types import ExtractedDocument, RawBlock


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

NS = {"x": MAIN_NS, "r": REL_NS, "pr": PKG_REL_NS}


class XlsxExtractor(BaseExtractor):
    supported_extensions = (".xlsx",)
    name = "xlsx"

    def extract(self, path: Path) -> ExtractedDocument:
        with ZipFile(path) as archive:
            workbook_xml = ET.fromstring(archive.read("xl/workbook.xml"))
            workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            shared_strings = self._load_shared_strings(archive)

            relationship_map = {
                rel.attrib.get("Id"): rel.attrib.get("Target", "")
                for rel in workbook_rels.findall("pr:Relationship", NS)
            }

            blocks: list[RawBlock] = []
            text_parts: list[str] = []

            for sheet in workbook_xml.findall("x:sheets/x:sheet", NS):
                name = sheet.attrib.get("name", "Sheet")
                rel_id = sheet.attrib.get(f"{{{REL_NS}}}id", "")
                target = relationship_map.get(rel_id, "")
                if not target:
                    continue
                xml_path = f"xl/{target}" if not target.startswith("xl/") else target
                rows = self._read_sheet_rows(archive, xml_path, shared_strings)
                if not rows:
                    continue

                text_parts.append(f"Sheet: {name}")
                text_parts.extend(" | ".join(row) for row in rows)
                blocks.append(RawBlock(kind="heading", text=name, metadata={"sheet_name": name}))
                blocks.append(
                    RawBlock(
                        kind="table",
                        text="\n".join(" | ".join(row) for row in rows),
                        data=rows,
                        metadata={"sheet_name": name},
                    )
                )

        return ExtractedDocument(
            extractor_name=self.name,
            text="\n".join(text_parts),
            blocks=blocks,
        )

    def _load_shared_strings(self, archive: ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        values: list[str] = []
        for item in root.findall("x:si", NS):
            texts = []
            for node in item.findall(".//x:t", NS):
                if node.text:
                    texts.append(node.text)
            values.append("".join(texts))
        return values

    def _read_sheet_rows(self, archive: ZipFile, xml_path: str, shared_strings: list[str]) -> list[list[str]]:
        root = ET.fromstring(archive.read(xml_path))
        rows: list[list[str]] = []
        for row in root.findall(".//x:sheetData/x:row", NS):
            values = []
            for cell in row.findall("x:c", NS):
                value = self._cell_value(cell, shared_strings)
                values.append(value)
            if any(values):
                rows.append(values)
        return rows

    def _cell_value(self, cell: ET.Element, shared_strings: list[str]) -> str:
        cell_type = cell.attrib.get("t")
        value_node = cell.find("x:v", NS)
        inline_node = cell.find("x:is/x:t", NS)
        if inline_node is not None and inline_node.text:
            return inline_node.text.strip()
        if value_node is None or value_node.text is None:
            return ""
        raw = value_node.text.strip()
        if cell_type == "s":
            try:
                return shared_strings[int(raw)]
            except (ValueError, IndexError):
                return raw
        return raw

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.types import ExtractedDocument, RawBlock


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"

NS = {"w": W_NS, "a": A_NS, "pic": PIC_NS}


class DocxExtractor(BaseExtractor):
    supported_extensions = (".docx",)
    name = "docx"

    def extract(self, path: Path) -> ExtractedDocument:
        with ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
            styles_xml = archive.read("word/styles.xml") if "word/styles.xml" in archive.namelist() else None

        style_map = self._load_styles(styles_xml) if styles_xml else {}
        root = ET.fromstring(document_xml)
        body = root.find("w:body", NS)
        blocks: list[RawBlock] = []
        full_text: list[str] = []
        image_count = 0

        if body is None:
            return ExtractedDocument(extractor_name=self.name, text="", blocks=blocks)

        for child in list(body):
            tag = self._strip_namespace(child.tag)
            if tag == "p":
                text = self._paragraph_text(child).strip()
                style_hint = self._paragraph_style(child, style_map)
                has_numbering = child.find(".//w:numPr", NS) is not None
                image_refs = child.findall(".//a:blip", NS) or child.findall(".//pic:blipFill", NS)
                image_count += len(image_refs)
                if image_refs:
                    for idx, _ in enumerate(image_refs):
                        blocks.append(RawBlock(kind="image", metadata={"image_index": image_count + idx}))

                if not text:
                    continue
                kind = "paragraph"
                if style_hint.lower().startswith("heading"):
                    kind = "heading"
                elif has_numbering or text.startswith(("-", "*", "•")):
                    kind = "list_item"
                full_text.append(text)
                blocks.append(
                    RawBlock(
                        kind=kind,
                        text=text,
                        style_hint=style_hint or None,
                    )
                )
            elif tag == "tbl":
                rows = self._table_rows(child)
                if rows:
                    blocks.append(
                        RawBlock(
                            kind="table",
                            text="\n".join(" | ".join(row) for row in rows),
                            data=rows,
                        )
                    )

        return ExtractedDocument(
            extractor_name=self.name,
            text="\n".join(full_text),
            blocks=blocks,
            metadata={"image_count": image_count},
        )

    def _load_styles(self, payload: bytes) -> dict[str, str]:
        root = ET.fromstring(payload)
        styles: dict[str, str] = {}
        for style in root.findall("w:style", NS):
            style_id = style.attrib.get(f"{{{W_NS}}}styleId", "")
            name_node = style.find("w:name", NS)
            if style_id and name_node is not None:
                styles[style_id] = name_node.attrib.get(f"{{{W_NS}}}val", style_id)
        return styles

    def _paragraph_text(self, paragraph: ET.Element) -> str:
        texts = []
        for node in paragraph.findall(".//w:t", NS):
            if node.text:
                texts.append(node.text)
        return "".join(texts)

    def _paragraph_style(self, paragraph: ET.Element, style_map: dict[str, str]) -> str:
        style = paragraph.find("w:pPr/w:pStyle", NS)
        if style is None:
            return ""
        style_id = style.attrib.get(f"{{{W_NS}}}val", "")
        return style_map.get(style_id, style_id)

    def _table_rows(self, table: ET.Element) -> list[list[str]]:
        rows: list[list[str]] = []
        for row in table.findall("w:tr", NS):
            values = []
            for cell in row.findall("w:tc", NS):
                values.append(self._cell_text(cell))
            if any(value for value in values):
                rows.append(values)
        return rows

    def _cell_text(self, cell: ET.Element) -> str:
        parts = []
        for paragraph in cell.findall("w:p", NS):
            text = self._paragraph_text(paragraph).strip()
            if text:
                parts.append(text)
        return " ".join(parts)

    @staticmethod
    def _strip_namespace(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

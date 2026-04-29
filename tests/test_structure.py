from app.pipeline.transform.structure import build_structure
from app.pipeline.types import ExtractedDocument, RawBlock


def test_build_structure_detects_headings_and_tables() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="1. Introduction\nBody",
        blocks=[
            RawBlock(kind="paragraph", text="1. Introduction", page_num=1),
            RawBlock(kind="paragraph", text="Body text", page_num=1),
            RawBlock(kind="table", data=[["A", "B"], ["1", "2"]], text="A | B\n1 | 2", page_num=1),
        ],
        page_count=1,
    )

    sections, blocks, tables, images, chunks = build_structure(extracted)

    assert len(sections) >= 2
    assert any(block.type == "heading" for block in blocks)
    assert len(tables) == 1
    assert len(images) == 0
    assert chunks


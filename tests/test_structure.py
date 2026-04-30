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


def test_text_chunk_carries_direct_section_and_page_context() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="1. Ecology\nBaseline text",
        blocks=[
            RawBlock(kind="paragraph", text="1. Ecology", page_num=2),
            RawBlock(kind="paragraph", text="Baseline text for source backed handoff.", page_num=3),
        ],
        page_count=3,
    )

    _sections, _blocks, _tables, _images, chunks = build_structure(extracted)
    chunk = next(item for item in chunks if "Baseline text" in item.text)

    assert chunk.content_type == "text"
    assert chunk.section_title == "1. Ecology"
    assert chunk.section_path == ["Document", "1. Ecology"]
    assert chunk.page_start == 2
    assert chunk.page_end == 3
    assert chunk.table_id is None


def test_table_row_chunk_carries_table_id_only_when_linked_to_table() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="1. Tables\nA B",
        blocks=[
            RawBlock(kind="paragraph", text="1. Tables", page_num=1),
            RawBlock(kind="table", data=[["Pollutant", "Value"], ["NOx", "10"]], text="Pollutant | Value", page_num=4),
        ],
        page_count=4,
    )

    _sections, _blocks, tables, _images, chunks = build_structure(extracted)
    table_row_chunk = next(item for item in chunks if item.content_type == "table_row")

    assert tables[0].table_id == table_row_chunk.table_id
    assert table_row_chunk.page_start == 4
    assert table_row_chunk.page_end == 4


def test_table_row_chunk_carries_readable_context_headers_and_row_values() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="1. Расчет выбросов\nTable",
        blocks=[
            RawBlock(kind="paragraph", text="1. Расчет выбросов", page_num=1),
            RawBlock(
                kind="table",
                data=[
                    ["Код", "Загрязняющее вещество", "Выброс г/с"],
                    ["0301", "Азота диоксид", "0.12"],
                ],
                text="Код | Загрязняющее вещество | Выброс г/с\n0301 | Азота диоксид | 0.12",
                page_num=5,
                metadata={"sheet_name": "Лист1"},
            ),
        ],
        page_count=5,
    )

    _sections, _blocks, _tables, _images, chunks = build_structure(extracted)
    table_row_chunk = next(item for item in chunks if item.content_type == "table_row")

    assert table_row_chunk.table_title == "1. Расчет выбросов"
    assert table_row_chunk.table_headers == ["Код", "Загрязняющее вещество", "Выброс г/с"]
    assert table_row_chunk.table_row_index == 2
    assert table_row_chunk.table_column_values == {
        "Код": "0301",
        "Загрязняющее вещество": "Азота диоксид",
        "Выброс г/с": "0.12",
    }
    assert table_row_chunk.row_count == 2
    assert table_row_chunk.column_count == 3
    assert "Таблица tbl-" in table_row_chunk.text
    assert "Раздел: Document > 1. Расчет выбросов" in table_row_chunk.text
    assert "Колонки: Код: 0301" in table_row_chunk.text
    assert "Азота диоксид" in table_row_chunk.text
    assert "0.12" in table_row_chunk.text


def test_table_row_chunk_without_headers_keeps_lexical_values_without_inventing_headers() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="Table",
        blocks=[
            RawBlock(kind="table", data=[["NOx", "10"]], text="NOx | 10", page_num=2),
        ],
        page_count=2,
    )

    _sections, _blocks, _tables, _images, chunks = build_structure(extracted)
    table_row_chunk = next(item for item in chunks if item.content_type == "table_row")

    assert table_row_chunk.table_headers == []
    assert table_row_chunk.table_column_values == {}
    assert "Значения строки: NOx; 10" in table_row_chunk.text
    assert "NOx" in table_row_chunk.text
    assert "10" in table_row_chunk.text

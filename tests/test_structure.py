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


def test_toc_heading_does_not_become_parent_for_body_sections() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="СОДЕРЖАНИЕ\n1. ОБЩИЕ СВЕДЕНИЯ О ПРЕДПРИЯТИИ\nBody",
        blocks=[
            RawBlock(kind="paragraph", text="СОДЕРЖАНИЕ"),
            RawBlock(kind="paragraph", text="1. ОБЩИЕ СВЕДЕНИЯ О ПРЕДПРИЯТИИ"),
            RawBlock(kind="paragraph", text="Описание предприятия и экологического проекта."),
        ],
    )

    sections, _blocks, _tables, _images, chunks = build_structure(extracted)
    body_section = next(section for section in sections if section.title == "1. ОБЩИЕ СВЕДЕНИЯ О ПРЕДПРИЯТИИ")
    body_chunk = next(chunk for chunk in chunks if "Описание предприятия" in chunk.text)

    assert body_section.parent_id == "sec-0"
    assert body_chunk.section_path == ["Document", "1. ОБЩИЕ СВЕДЕНИЯ О ПРЕДПРИЯТИИ"]
    assert "СОДЕРЖАНИЕ" not in body_chunk.section_path


def test_repeated_heading_prefix_is_deduplicated_in_chunk_text() -> None:
    for heading in ("АННАТОЦИЯ", "ВВЕДЕНИЕ", "1.1 Название"):
        extracted = ExtractedDocument(
            extractor_name="test",
            text=f"{heading}\n{heading}\nBody",
            blocks=[
                RawBlock(kind="paragraph", text=heading),
                RawBlock(kind="paragraph", text=heading),
                RawBlock(kind="paragraph", text="Полезный текст раздела для handoff."),
            ],
        )

        _sections, _blocks, _tables, _images, chunks = build_structure(extracted)
        chunk = next(item for item in chunks if "Полезный текст" in item.text)

        assert chunk.text.splitlines().count(heading) == 1
        assert f"{heading}\n{heading}" not in chunk.text


def test_heading_only_section_does_not_emit_standalone_text_chunk() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="ВВЕДЕНИЕ",
        blocks=[RawBlock(kind="paragraph", text="ВВЕДЕНИЕ")],
    )

    _sections, _blocks, _tables, _images, chunks = build_structure(extracted)

    assert chunks == []


def test_service_signature_table_is_preserved_as_text_not_table_chunk() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="УТВЕРЖДАЮ\nДолжность Подпись",
        blocks=[
            RawBlock(
                kind="table",
                data=[["УТВЕРЖДАЮ"], ["Должность", "Подпись", "Ф.И.О."]],
                text="УТВЕРЖДАЮ\nДолжность | Подпись | Ф.И.О.",
            ),
        ],
    )

    _sections, blocks, tables, _images, chunks = build_structure(extracted)

    assert tables == []
    assert blocks[0].type == "paragraph"
    assert blocks[0].metadata["table_classification"] == "service_text"
    assert all(chunk.content_type != "table_row" for chunk in chunks)


def test_title_approval_signature_table_with_placeholders_is_demoted_to_service_text() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text='ВЕЩЕСТВ В АТМОСФЕРУ\n"Утверждено"\nКоммерческий директор',
        blocks=[
            RawBlock(kind="paragraph", text="ВЕЩЕСТВ В АТМОСФЕРУ"),
            RawBlock(
                kind="table",
                data=[
                    ['"Утверждено"', "", ""],
                    ["Коммерческий директор ООО «БИЖУ»", "/__________________/", "Неизвестный А.Н."],
                    ["", "(подпись)", ""],
                    ["/_______/", "/___________/", "2023 г."],
                    ["(число)", "(месяц)", ""],
                ],
                text=(
                    '"Утверждено" Коммерческий директор ООО «БИЖУ» '
                    "/__________________/ Неизвестный А.Н. (подпись) "
                    "/_______/ /___________/ 2023 г. (число) (месяц)"
                ),
            ),
        ],
    )

    _sections, blocks, tables, _images, chunks = build_structure(extracted)

    assert tables == []
    service_block = next(block for block in blocks if block.metadata.get("table_classification") == "service_text")
    assert service_block.type == "paragraph"
    assert '"Утверждено"' in (service_block.text or "")
    assert all(chunk.content_type != "table_row" for chunk in chunks)
    assert all(chunk.table_id is None for chunk in chunks)


def test_single_cell_title_approval_signature_table_is_demoted_to_service_text() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text='"Утверждено" Коммерческий директор',
        blocks=[
            RawBlock(
                kind="table",
                data=[
                    [
                        '"Утверждено" Коммерческий директор ООО «БИЖУ» /__________________/ '
                        "Неизвестный А.Н. (подпись) /_______/ /___________/ 2023 г. (число) (месяц)"
                    ]
                ],
                text=(
                    '"Утверждено" Коммерческий директор ООО «БИЖУ» /__________________/ '
                    "Неизвестный А.Н. (подпись) /_______/ /___________/ 2023 г. (число) (месяц)"
                ),
            ),
        ],
    )

    _sections, blocks, tables, _images, chunks = build_structure(extracted)

    assert tables == []
    assert blocks[0].type == "paragraph"
    assert blocks[0].metadata["table_classification"] == "service_text"
    assert all(chunk.table_id is None for chunk in chunks)


def test_real_table_chunk_logic_is_preserved() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="1. Data\nTable",
        blocks=[
            RawBlock(kind="paragraph", text="1. Data"),
            RawBlock(
                kind="table",
                data=[
                    ["Код", "Вещество", "Выброс"],
                    ["0301", "Азота диоксид", "0.12"],
                    ["0330", "Сера диоксид", "0.05"],
                ],
                text="Код | Вещество | Выброс\n0301 | Азота диоксид | 0.12\n0330 | Сера диоксид | 0.05",
            ),
        ],
    )

    _sections, _blocks, tables, _images, chunks = build_structure(extracted)

    assert len(tables) == 1
    assert [chunk.content_type for chunk in chunks].count("table_row") == 2


def test_real_docx_table_with_service_word_but_row_data_is_preserved() -> None:
    extracted = ExtractedDocument(
        extractor_name="test",
        text="1. Реестр согласования\nTable",
        blocks=[
            RawBlock(kind="paragraph", text="1. Реестр согласования"),
            RawBlock(
                kind="table",
                data=[
                    ["N", "Должность", "Комментарий", "Дата"],
                    ["1", "Инженер", "Проверил расчет выбросов по разделу 2", "2023-01-10"],
                    ["2", "Главный специалист", "Согласовал исходные данные по разделу 3", "2023-01-11"],
                    ["3", "Руководитель проекта", "Принял замечания без подписи в исходном файле", "2023-01-12"],
                ],
                text=(
                    "N | Должность | Комментарий | Дата\n"
                    "1 | Инженер | Проверил расчет выбросов по разделу 2 | 2023-01-10\n"
                    "2 | Главный специалист | Согласовал исходные данные по разделу 3 | 2023-01-11\n"
                    "3 | Руководитель проекта | Принял замечания без подписи в исходном файле | 2023-01-12"
                ),
            ),
        ],
    )

    _sections, blocks, tables, _images, chunks = build_structure(extracted)

    assert len(tables) == 1
    assert any(block.type == "table" for block in blocks)
    assert [chunk.content_type for chunk in chunks].count("table_row") == 3

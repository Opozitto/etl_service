# FINISH_LINE

## Текущий baseline

- ETL baseline запускается end-to-end в подтверждённом локальном окружении.
- Поддерживаемые форматы документов: `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`.
- Standalone `jpg` / `jpeg` / `png` принимаются только в metadata-only режиме без OCR.
- `HEIC` / `HEIF` / `TIFF` / `TIF` / `BMP` / `WEBP` остаются неподдерживаемыми image-like форматами.
- `XLS` и `XLSX` извлекаются в JSON, попадают в chunks/search/ask и используют flattened lexical retrieval.
- Row-level chunks для таблиц добавляют sheet/table/row/column-value textual context, но это всё ещё lexical retrieval, а не table-aware analytics.
- Customer demo smoke runner доступен как read-only CLI helper и честно показывает текущие ограничения baseline.

## Что подтверждено, а что нет

- Подтверждено:
  - source-backed search;
  - source-backed ask / extractive QA;
  - corpus audit visibility;
  - corpus rebuild;
  - spreadsheet table retrieval с row-level context.
- Не подтверждено:
  - OCR;
  - LLM generation;
  - summarization / draft generation;
  - semantic retrieval;
  - vector DB;
  - full RAG;
  - table-aware analytics;
  - external proprietary APIs.

## Следующий выбор

Ниже не реализованные варианты следующего этапа:

- Stage 19A: retrieval evaluation v2 / table-aware evaluation set.
- Stage 19B: OCR intake spike for `jpg` / `png` scans.
- Stage 19C: summarization / draft generation spike.
- Stage 19D: prototype API demo packaging.

## Note

- Stage 18 completed the governance / roadmap audit and aligned the project docs with the current code baseline.

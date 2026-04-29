# FINISH_LINE

## Завершённый baseline

- ETL baseline запускается end-to-end в подтверждённом локальном окружении.
- Поддерживаемые форматы baseline продолжают работать: `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, плюс baseline image presence handling.
- `XLSX` tables извлекаются, сохраняются в JSON, chunk'аются и попадают в local retrieval path.
- Старый бинарный `XLS` остаётся явно unsupported spreadsheet format с русским user-facing message.
- Standalone `jpg`/`jpeg`/`png` image intake работает metadata-only, фиксирует `images_detected=True`, `ocr_used=False` и сохраняет обычный JSON result.
- Stage 12 закрыт: known unsupported image-like formats `HEIC`/`HEIF`/`TIFF`/`TIF`/`BMP`/`WEBP` остаются unsupported с русским user-facing message, а API smoke покрыт тестом.
- JSON output contract остаётся стабильным для обработанных документов, corpus index и manifest.
- API flow продолжает работать для upload/process, fetch/list documents, corpus stats, corpus reindex, search и ask.
- Минимальное retrieval proof остаётся доступным и возвращает top hits из локального demo corpus.
- Реализация остаётся в рамках текущего local filesystem storage/index подхода.

## Pilot AI-service track

- После закрытия Stage 7–9 проект получает отдельный pilot track, привязанный к расширенному брифу заказчика.
- Этот track не означает, что OCR, semantic retrieval, полноценный RAG, vector DB или LLM generation уже готовы.
- Следующие этапы должны вести к source-backed QA, summarization / generation spike и prototype integration; `XLS` decision для baseline закрыт.

## Вне текущего baseline

- Полноценный RAG-продукт.
- Vector database или внешний search backend.
- LLM generation или answer synthesis как уже готовая функция.
- OCR как подтверждённая production capability.
- Сложный observability stack.
- Новые product surfaces вне текущего ETL/search service.

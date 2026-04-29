# FINISH_LINE

## ОБЯЗАТЕЛЬНО ЗАВЕРШИТЬ

- ETL baseline запускается end-to-end в подтверждённом локальном окружении.
- Поддерживаемые форматы продолжают работать: `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, плюс baseline image presence handling.
- JSON output contract остаётся стабильным для обработанных документов, corpus index и записей manifest.
- Поток API продолжает работать для upload/process, fetch/list documents, corpus stats, corpus reindex, search и ask.
- Минимальное retrieval proof остаётся доступным и возвращает top hits из локального demo corpus.
- Реализация остаётся в рамках текущего локального filesystem storage/index подхода.

## ПОСЛЕ ЗАВЕРШЕНИЯ

- Включение OCR и OCR-специфичного extraction flow.
- Semantic retrieval поверх текущего baseline.
- Улучшение ranking за пределами текущего локального search behavior.
- Расширенная evaluation и более богатые regression checks для retrieval quality.
- Улучшенный batch reporting и observability в рамках текущей продуктовой границы.

## ПОЗЖЕ / ВНЕ ОБЛАСТИ

- Полноценный RAG-продукт.
- Vector database или внешний search backend.
- LLM generation или answer synthesis за пределами текущего baseline proof.
- Сложный observability stack.
- Новые product surfaces вне текущего ETL/search service.

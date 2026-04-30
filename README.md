# ETL Service

Автономный ETL-микросервис для извлечения структуры из документов и подготовки данных для последующей обработки и задач поиска.

## Что умеет baseline

- принимает документы через API или пакетную CLI-обработку
- поддерживает `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`
- `xlsx` и `xls` извлекают таблицы, сохраняют их в JSON и дают табличный текст в retrieval path
- `jpg`/`jpeg`/`png` фиксируют как наличие изображений без OCR
- извлекает текст, таблицы, базовые метаданные и факт наличия изображений
- строит структурированный JSON с разделами, блоками и таблицами
- сохраняет результаты локально в `storage/`
- индексирует все обработанные документы и позволяет делать простой поиск по корпусу
- Stage 13 historically treated `XLS` as unsupported, but Stage 14 superseded that state and `.xls` is now a confirmed baseline format.

## Структура проекта

- `app/api` — FastAPI endpoint'ы
- `app/pipeline` — extract / transform / load
- `app/storage` — файловое хранилище артефактов
- `app/search` — локальный retrieval по обработанным документам
- `tests` — тесты
- `scripts` — CLI для пакетной обработки директории

## Быстрый старт

```bash
conda run -n etl_env python -m pip install -e .[dev]
conda run -n etl_env uvicorn app.main:app --reload
```

## Полезные endpoint'ы

- `GET /health`
- `POST /api/v1/documents/process`
- `GET /api/v1/documents/{document_id}`
- `GET /api/v1/documents`
- `POST /api/v1/search`
- `POST /api/v1/ask`
- `GET /api/v1/corpus/stats`
- `POST /api/v1/corpus/reindex`
- `GET /api/v1/corpus/manifest`

Поток API подтверждён тестом `tests/test_api.py`.

## `/api/v1/ask`

`AskResponse` включает `question`, `answer`, `sources`, `hits`, `strategy`.
`sources` — source-backed evidence snippets, а `hits` сохранён для обратной совместимости.
Для `xlsx`/`xls`/табличных документов ответы строятся через flattened lexical retrieval по чанкам, а не через полноценную table-aware логику.
Для `xlsx`/`xls` table chunks теперь получают row-level context с sheet/table/row/column-value текстом, что улучшает lexical retrieval по строкам таблиц без изменения API contract.
Если в корпусе нет ответа, сервис возвращает `нет информации в корпусе`.

## Batch обработка директории

```bash
conda run -n etl_env python -m scripts.batch_process --input-dir first_test_data
```

С отчётом:

```bash
conda run -n etl_env python -m scripts.batch_process --input-dir first_test_data --report-path storage/index/last_batch_report.json
```

## Customer demo smoke runner

```bash
conda run -n etl_env python -m scripts.demo_customer_flow
```

Optional JSON report:

```bash
conda run -n etl_env python -m scripts.demo_customer_flow --json-report-path storage/index/customer_demo_report.json
```

Default mode is read-only. The optional JSON report path is a runtime artifact, and `--refresh-index` is the only mode that may update `storage/index`.
This demo reports the current baseline only: OCR, LLM generation, summarization, vector DB, semantic retrieval, and full RAG are not implemented.
Вывод демо-проверки теперь русскоязычный и ориентирован на read-only просмотр текущего состояния корпуса; для более явного row-level table context при необходимости можно запустить `--refresh-index`.

## Пересборка индекса корпуса

```bash
conda run -n etl_env python -m scripts.rebuild_corpus
```

Индекс корпуса хранится в `storage/index/corpus_index.json` и используется поиском, чтобы не сканировать все JSON-результаты на каждый запрос.

## Минимальная retrieval-проверка

После пакетной обработки можно проверить, что структура документа уже даёт полезный корпус для задач последующей обработки:

```bash
conda run -n etl_env python -m scripts.demo_search --query "экология проект"
```

Скрипт поднимает простой локальный retrieval по чанкам из всех сохранённых JSON-результатов в `storage/results`.

## Corpus quality audit

Для read-only аудита качества корпуса доступны команды:

```bash
conda run -n etl_env python -m scripts.audit_corpus
conda run -n etl_env python -m scripts.audit_corpus --report-path storage/index/last_corpus_audit.json
```

Скрипт читает сохранённые JSON-результаты и при наличии corpus index / manifest, а затем печатает краткий summary без изменения `storage/results` и `storage/index`.

## Очистка дубликатов в storage

```bash
conda run -n etl_env python -m scripts.cleanup_storage
conda run -n etl_env python -m scripts.cleanup_storage --apply
```

## OCR

OCR не входит в текущий baseline. `jpg`/`jpeg`/`png` поддерживаются только как standalone image input и используются для фиксации наличия изображений, без OCR.
`HEIC`/`HEIF`/`TIFF`/`TIF`/`BMP`/`WEBP` сейчас намеренно остаются неподдерживаемыми image-like форматами до отдельной проверки local decoding/OCR.
Для standalone image intake в `processing_info.features` фиксируются `images_detected=True` и `ocr_used=False`, а результат сохраняется в обычный JSON.
Для ручной проверки image intake можно использовать `first_test_data/Справка (таблица).jpg` и `first_test_data/Справка (таблица).png`; это metadata-only standalone image intake без OCR, и они не нужны для автоматических тестов.

## Поддержка DOC

Для старых файлов `DOC` baseline использует локальный `LibreOffice` (`soffice`) и конвертирует документ в `DOCX` перед извлечением. Внешние API не используются.

## Stage 14 note

- `.xls` is now supported at baseline level through `XlsExtractor`.
- `.xls` and `.xlsx` share the same flattened table extraction contract for search/ask, with additional row-level lexical chunks for better row/value retrieval.
- Advanced Excel semantics such as formulas, macros, styles, merged cells, and hidden-sheet behavior remain out of scope.
- Stage 13's unsupported-XLS decision is historical only and has been superseded by Stage 14.

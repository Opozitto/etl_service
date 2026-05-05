# ETL Service

Автономный ETL-микросервис для извлечения структуры из документов и подготовки данных для последующей обработки и задач поиска.

## Что умеет baseline

- принимает документы через API или пакетную CLI-обработку
- поддерживает `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`
- `xlsx` и `xls` извлекают таблицы, сохраняют их в JSON и дают табличный текст в retrieval path
- `jpg`/`jpeg`/`png` поддерживают optional local OCR baseline: при наличии локального engine текст извлекается, а при его отсутствии сохраняется metadata-only OCR-candidate поведение
- извлекает текст, таблицы, базовые метаданные и факт наличия изображений
- строит структурированный JSON с разделами, блоками и таблицами
- сохраняет результаты локально в `storage/`
- индексирует все обработанные документы и позволяет делать простой поиск по корпусу
- Исторически Stage 13 считал `XLS` неподдерживаемым, но Stage 14 уже заменил это состояние: `.xls` теперь является подтверждённым baseline-форматом.

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
- `GET /api/v1/corpus/requirements`
- `GET /api/v1/corpus/tables`

Поток API подтверждён тестом `tests/test_api.py`.

## `/api/v1/ask`

`AskResponse` включает `question`, `answer`, `sources`, `hits`, `strategy`.
`sources` — это source-backed evidence snippets, а `hits` сохранён для обратной совместимости.
Для `xlsx`/`xls` и табличных документов ответы строятся через flattened lexical retrieval по чанкам, а не через полноценную table-aware логику.
Для `xlsx`/`xls` table chunks теперь получают row-level context с `sheet` / `table` / `row` / `column-value` текстом, что улучшает lexical retrieval по строкам таблиц без изменения API contract.
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

Опциональный JSON-отчёт:

```bash
conda run -n etl_env python -m scripts.demo_customer_flow --json-report-path storage/index/customer_demo_report.json
```

Режим по умолчанию read-only. Путь для опционального JSON-отчёта является runtime artifact, а `--refresh-index` — единственный режим, который может обновить `storage/index`.
Этот demo показывает только текущий baseline: OCR, LLM generation, summarization, vector DB, semantic retrieval и full RAG не реализованы.
Вывод демо-проверки русскоязычный и ориентирован на read-only просмотр текущего состояния корпуса; в Stage 19.1 он также показывает OCR candidate summary без запуска OCR. Для более явного row-level table context при необходимости можно запустить `--refresh-index`.

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

## Requirements extraction v1

Для read-only извлечения возможных требований из уже обработанных JSON доступен deterministic source-backed слой:

```bash
conda run -n etl_env python -m scripts.extract_requirements
conda run -n etl_env python -m scripts.extract_requirements --json-report-path reports/requirements_v1.json
```

Скрипт читает `storage/results`, возвращает extractive candidates с `document_id`, `filename`, source context, category, score и matched terms. JSON-отчёт пишется только по явному `--json-report-path`. Это не LLM, не RAG, не генерация новых требований и не юридическая/compliance-гарантия.

## Table evidence evaluation

Для read-only оценки табличных источников и поиска возможных входных данных для экологических расчетов доступен deterministic source-backed слой:

```bash
conda run -n etl_env python -m scripts.evaluate_tables
conda run -n etl_env python -m scripts.evaluate_tables --json-report-path reports/table_evidence_v1.json
```

Скрипт читает уже обработанные JSON из `storage/results`, показывает найденные таблицы, source-backed preview, категории и matched terms. JSON-отчет пишется только по явному `--json-report-path`. Это не SQL/table analytics, не table reasoning и не автоматические расчеты.

## OCR

OCR для standalone `jpg`/`jpeg`/`png` теперь optional local baseline: если локальный `tesseract` доступен, сервис извлекает текст и сохраняет его в обычный document output, чтобы он попадал в blocks/chunks/search/ask path.
Если локальный OCR engine недоступен, упал или вернул пустой текст, сохраняется metadata-only OCR-candidate поведение Stage 19.1.
В `processing_info.features` для image-only intake теперь могут появляться `ocr_used`, `ocr_candidate`, `ocr_engine`, `ocr_text_length` и `ocr_status`; top-level contract при этом не расширяется.
`pdf` без meaningful extracted text / chunks по-прежнему может быть conservatively отмечен как `possible_scanned_pdf` / OCR candidate, но страницы не рендерятся в изображения и OCR для scanned PDF не запускается.
`HEIC`/`HEIF`/`TIFF`/`TIF`/`BMP`/`WEBP` по-прежнему остаются неподдерживаемыми image-like форматами.
Read-only audit и customer demo runner теперь показывают summary по OCR candidates и OCR-used documents без изменения storage.
Для ручной проверки OCR engine и установленных language packs можно использовать `conda run -n etl_env python -m scripts.check_ocr`.

### OCR smoke/eval

Для read-only smoke/eval проверки качества OCR на sample images можно использовать:

```bash
conda run -n etl_env python -m scripts.evaluate_ocr
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path tmp/ocr_smoke_report.json
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path tmp/ocr_smoke_report.json --language rus+eng
```

Этот script читает входные image samples, использует Stage 20 OCR adapter и не пишет в `storage/index`, `storage/results` или `storage/uploads`.
`--language` задаёт Tesseract language config для smoke/eval; для русских документов рекомендуется `--language rus+eng`, если эти language packs установлены.
Это smoke/eval слой для проверки readiness, а не production OCR quality guarantee: качество зависит от изображения, установленных языков Tesseract, preprocessing и будущего OCR module design.
Scanned PDF OCR и OCR embedded images inside DOCX/PDF не входят в baseline; external/proprietary OCR API не используются.
Будущий OCR module должен сохранять provenance: source path/name, page, artifact/image id, OCR engine/version, language config, confidence if available, processing timestamp и source modality.
OCR-derived chunks в будущем должны быть явно отмечены как OCR-derived evidence и не смешиваться молча с обычным text layer.
Table OCR не должен выдаваться за structured table extraction без отдельной layout/table model.

## Поддержка DOC

Для старых файлов `DOC` baseline использует локальный `LibreOffice` (`soffice`) и конвертирует документ в `DOCX` перед извлечением. Внешние API не используются.

## Примечание Stage 14

- `.xls` теперь поддерживается на baseline-уровне через `XlsExtractor`.
- `.xls` и `.xlsx` используют один и тот же flattened table extraction contract для search/ask, а дополнительные row-level lexical chunks улучшают поиск по строкам и значениям.
- Advanced Excel semantics вроде formulas, macros, styles, merged cells и hidden-sheet behavior остаются вне scope.
- Решение Stage 13 о неподдержке `XLS` остаётся только исторической отметкой и уже заменено Stage 14.

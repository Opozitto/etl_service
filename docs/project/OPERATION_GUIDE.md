# OPERATION GUIDE

## Назначение документа

Этот документ описывает эксплуатацию ETL service для финальной сдачи и передачи проекта.

Текущий проект - это ETL/source-backed handoff baseline: он извлекает структуру документов, готовит `StructuredDocument` JSON, строит локальные chunks/index и поддерживает source-backed search/ask. Это не full RAG/LLM product: генерация LLM-ответов, semantic retrieval, embeddings/vector DB, scanned PDF OCR, embedded image OCR, table analytics, production UI и external proprietary API не входят в подтвержденный baseline.

## Уровень 1: короткий запуск

Установка dev-зависимостей:

```powershell
conda run -n etl_env python -m pip install -e .[dev]
```

Быстрая regression-проверка в локальном окружении:

```powershell
conda run -n etl_env python -m pytest -q
```

Customer demo flow:

```powershell
conda run -n etl_env python -m scripts.demo_customer_flow
```

Проверка структуры одного файла без загрязнения production `storage/`:

```powershell
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\file.docx"
```

Проверка локального OCR engine и языков Tesseract:

```powershell
conda run -n etl_env python -m scripts.check_ocr
```

Если demo/eval/API smoke изменили production storage, восстановить tracked baseline:

```powershell
git restore storage/index storage/results storage/uploads
```

## Уровень 2: средний маршрут с объяснением логики

Основной pipeline проекта:

```text
intake -> extractor -> StructuredDocument JSON -> blocks/sections/tables/images -> chunks -> index/search/ask/eval
```

Сервис принимает документы через API или CLI, выбирает extractor по формату, строит структурированный JSON с metadata, sections, blocks, tables/images и processing diagnostics. Затем transformer готовит chunks для локального lexical retrieval. Search и ask работают source-backed: они возвращают evidence из корпуса и честно показывают no-hit поведение, если информации нет.

Почему здесь нет полноценного RAG/LLM: проект закрывает первый эксплуатационный слой - надежное извлечение, структурирование, индексацию, source-backed evidence и handoff diagnostics. Генеративная модель, embeddings/vector DB, semantic retrieval/reranking и production answer synthesis требуют отдельной реализации, оценки качества и контроля источников.

Зачем нужны основные эксплуатационные документы и скрипты:

- `scripts.demo_customer_flow` - read-only customer smoke текущего baseline: health of corpus, search/ask/table/OCR-candidate visibility и honest limitations.
- `scripts.inspect_document_structure` - проверка одного explicit файла в изолированном workspace, полезная для handoff/review до добавления файла в regular corpus flow.
- `scripts.audit_rag_chunks` - read-only диагностика chunk quality, compact taxonomy, table-linked context и handoff limitations.
- `scripts.validate_external_example_data` - workflow для external `D:\Projects\etl_service_backup\Example_data` как path-only evidence dataset, с обработкой только в `.runtime_eval` или другом explicit temporary workspace.
- `scripts.evaluate_ocr` - smoke/eval standalone `jpg`/`jpeg`/`png` OCR через локальный Tesseract, если он установлен.
- `scripts.evaluate_qa_dataset` - retrieval/source-backed QA readiness evaluation по QA CSV/TSV и уже обработанным JSON.
- `docs/project/METRICS_AND_ACCEPTANCE.md` - финальные quality gates и acceptance criteria для обработки, chunks, table context, search/ask, OCR smoke и operational cleanup.
- `experiments/README.md` - entry point для reproducible experiments/evaluation workflows: smoke/regression, single-file inspection, corpus/chunk audits, QA readiness, external validation, OCR smoke и requirements/table evidence.

Рекомендуемый порядок демонстрации:

1. Health/tests: установить dev-зависимости и выполнить локальную regression-проверку.
2. Demo flow: запустить `scripts.demo_customer_flow`.
3. Inspect one file: показать `scripts.inspect_document_structure` на одном explicit файле.
4. Chunk quality / external validation if needed: выполнить read-only chunk audit или bounded external validation в `.runtime_eval`.
5. OCR smoke if local Tesseract installed: проверить `scripts.check_ocr`, затем standalone image smoke через `scripts.evaluate_ocr --language rus+eng`.

## Уровень 3: подробная эксплуатация

### Требования окружения

- Windows.
- Conda env `etl_env`.
- Python 3.10 внутри `etl_env`.
- Local Tesseract optional only: нужен только для standalone `jpg`/`jpeg`/`png` OCR smoke/baseline.
- Для DOC baseline может использоваться локальный LibreOffice (`soffice`) для конвертации в DOCX, если он доступен.

### Установка

Dev install:

```powershell
conda run -n etl_env python -m pip install -e .[dev]
```

Dependency sanity:

```powershell
conda run -n etl_env python -m pytest -q tests/test_contracts.py::test_processed_document_contract_round_trip
```

Если эта focused-проверка не запускается из-за локального окружения, сначала проверить, что используется именно `etl_env`, а не глобальный interpreter из PATH.

### Запуск тестов

Полная проверка:

```powershell
conda run -n etl_env python -m pytest -q
```

Focused tests для single-file inspector:

```powershell
conda run -n etl_env python -m pytest -q tests/test_inspect_document_structure.py
```

На этой Windows-машине Codex sandbox может ловить `PermissionError` на pytest temp / `tmp_path`. Это ограничение sandbox ACL, а не дефект проекта. Source of truth для regression остается локальный запуск пользователем в `etl_env` вне sandbox.

### Работа с API

Запуск FastAPI/uvicorn:

```powershell
conda run -n etl_env uvicorn app.main:app --reload
```

Core endpoints текущего baseline:

- `GET /health`;
- `POST /api/v1/documents/process`;
- `GET /api/v1/documents/{document_id}`;
- `GET /api/v1/documents`;
- `POST /api/v1/search`;
- `POST /api/v1/ask`;
- `GET /api/v1/corpus/stats`;
- `POST /api/v1/corpus/reindex`;
- `GET /api/v1/corpus/manifest`;
- `GET /api/v1/corpus/requirements`;
- `GET /api/v1/corpus/tables`.

API обрабатывает документы в production `storage/`. Для временных smoke/eval маршрутов использовать `.runtime_eval` или explicit temporary workspace, если соответствующий скрипт поддерживает workspace path.

### Обработка документов

Batch/demo route для локального sample corpus:

```powershell
conda run -n etl_env python -m scripts.batch_process --input-dir first_test_data
conda run -n etl_env python -m scripts.rebuild_corpus
conda run -n etl_env python -m scripts.demo_search --query "экология проект"
```

Production storage route использует:

- `storage/uploads`;
- `storage/results`;
- `storage/index`.

Эти папки не использовать как scratch workspace для экспериментов. Если smoke/demo загрязнили production storage, восстановить tracked baseline:

```powershell
git restore storage/index storage/results storage/uploads
```

Temporary workspace route должен писать в `.runtime_eval` или другой explicit temporary path. Пример safe external validation workspace:

```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --process --run-eval --run-chunk-quality --clean-workspace --max-documents 5 --max-questions 20
```

### Single-file inspector

Console-only example:

```powershell
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\file.docx"
```

Markdown/JSON report example:

```powershell
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\file.docx" --output-path .runtime_eval\inspect_report.md --json-report-path .runtime_eval\inspect_report.json --clean-workspace
```

Inspector обрабатывает один explicit file path и по умолчанию использует `.runtime_eval\inspect_document_structure_workspace`. Не указывать `storage`, `storage/index`, `storage/results` или `storage/uploads` как workspace/output для inspection.

### Search / ask

Search и ask являются source-backed. Они ищут по локальному корпусу/chunks и возвращают evidence snippets, document/source context и deterministic location/citation hints where available.

No-hit behavior должен оставаться явным:

```text
нет информации в корпусе
```

Это extractive/source-backed QA path, а не LLM generation и не semantic retrieval.

### Tables

`XLS` и `XLSX` поддерживаются на baseline-уровне. Табличные данные извлекаются в JSON, попадают в chunks/search/ask и получают readable row-level context там, где доступны headers/row values.

Ограничение: это не table analytics, не SQL-like QA и не automatic calculations. Проект помогает найти source-backed строки, значения, headers и candidate tables, но не вычисляет показатели и не валидирует формулы.

### OCR

Проверка engine/language packs:

```powershell
conda run -n etl_env python -m scripts.check_ocr
```

Standalone image OCR smoke/eval:

```powershell
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path .runtime_eval\ocr_smoke_report.json --language rus+eng
```

Baseline OCR scope: standalone `jpg`, `jpeg`, `png` only. Если Tesseract или нужные language packs недоступны, поведение может быть fallback/metadata-only.

Не реализованы: scanned PDF OCR, embedded image OCR inside DOCX/PDF, layout/table OCR, external/proprietary OCR API.

### External Example_data validation

External dataset `D:\Projects\etl_service_backup\Example_data` используется только by path как external evidence dataset. Его нельзя копировать или коммитить в repository.

Strict expected-source mode может выбрать/обработать zero docs, если expected sources в QA-файле неоднозначны. Это workflow attention, а не успешная оценка качества chunks.

Exploratory bounded mode для non-empty ETL/chunk validation:

```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --source-scope all-supported --ambiguous-policy all --process --run-chunk-quality --clean-workspace --max-documents 10
```

Reports/workspaces должны оставаться в `.runtime_eval` или другом explicit temporary path. External files, runtime reports и workspace artifacts не коммитить.

### Metrics and acceptance

Метрики, acceptance gates и non-claims зафиксированы в [METRICS_AND_ACCEPTANCE.md](METRICS_AND_ACCEPTANCE.md).

Language/comment audit и правила будущей локализации зафиксированы в [LANGUAGE_AUDIT.md](LANGUAGE_AUDIT.md). При polish переводить только human-facing prose и не менять API/JSON/CLI identifiers, report fields, stage names или command examples.

Для финальной сдачи использовать этот guide как операционный маршрут, а `METRICS_AND_ACCEPTANCE.md` как quality/acceptance baseline.

### Runtime cleanup

Восстановить production storage после demo/eval/API smoke, если он изменился:

```powershell
git restore storage/index storage/results storage/uploads
```

`.runtime_eval` and `.pytest-run-temp` are local/runtime only. Их не коммитить.

Не коммитить:

- `storage/index`, `storage/results`, `storage/uploads` как runtime/scratch outputs;
- `.runtime_eval` reports/workspaces;
- `.pytest-run-temp`;
- external `D:\Projects\etl_service_backup\Example_data`;
- runtime reports из temporary/exploratory runs.

### Known limitations

- Нет full RAG.
- Нет LLM generation / answer synthesis.
- Нет semantic retrieval/reranking.
- Нет embeddings/vector DB.
- Нет scanned PDF OCR.
- Нет embedded DOCX/PDF image OCR.
- Нет layout/table OCR.
- Нет SQL/table analytics или automatic calculations.
- Нет production UI.
- Нет external proprietary API.
- OCR для standalone `jpg`/`jpeg`/`png` зависит от локального Tesseract и language packs.
- DOCX page metadata может быть недоступна; page context не должен выдумываться.
- Existing processed JSON не мигрируется автоматически после splitter/chunk improvements.
- External QA source matching может быть ambiguous/missing; это требует review, а не автоматического выбора первого файла.

### Typical final demonstration route

```powershell
conda run -n etl_env python -m pip install -e .[dev]
conda run -n etl_env python -m pytest -q
conda run -n etl_env python -m scripts.demo_customer_flow
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\file.docx" --output-path .runtime_eval\inspect_report.md --json-report-path .runtime_eval\inspect_report.json --clean-workspace
conda run -n etl_env python -m scripts.audit_rag_chunks --max-documents 1 --max-chunks-per-document 5
conda run -n etl_env python -m scripts.check_ocr
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path .runtime_eval\ocr_smoke_report.json --language rus+eng
git restore storage/index storage/results storage/uploads
git status --short
```

External validation для финальной демонстрации запускать только при доступном external path и понятной цели:

```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --source-scope all-supported --ambiguous-policy all --process --run-eval --run-chunk-quality --clean-workspace --max-documents 10 --max-questions 20
```

### Troubleshooting

CRLF warnings: `git diff --check` может показывать Windows line-ending warnings. Если это только line endings, не чинить весь репозиторий широким форматированием в docs-only stage.

UTF-8/mojibake: русскоязычные Markdown-файлы считать UTF-8. Если PowerShell console показывает mojibake, сначала проверить bytes/UTF-8 decode, BOM и replacement char `U+FFFD`; не переписывать файл только из-за кодовой страницы консоли.

Temp `PermissionError` in sandbox: в Codex sandbox на Windows возможен отказ доступа на test temp folders. Это локальное ограничение sandbox ACL. Не добавлять workaround в production code/tests; source of truth - локальный запуск пользователем в `etl_env`.

Missing Tesseract/languages: `scripts.check_ocr` покажет доступность engine и installed languages where available. Для русских standalone images рекомендуется `--language rus+eng`, если language packs установлены.

Unsupported formats: baseline formats - `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`; standalone OCR-capable image baseline - `jpg`, `jpeg`, `png`. `HEIC`, `HEIF`, `TIFF`, `TIF`, `BMP`, `WEBP` остаются unsupported image-like formats.

Ambiguous external expected sources: если external QA ожидает источник, который не находится однозначно, strict mode может выбрать zero docs. Для exploratory проверки использовать bounded `--source-scope all-supported` и/или `--ambiguous-policy all` с `--max-documents`.

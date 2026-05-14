# ETL Service

Автономный ETL-микросервис для извлечения структуры из документов и подготовки данных для последующей обработки, локального поиска и source-backed handoff.

Проект поставляется как clear baseline: готовые `storage/index`, `storage/results` и `storage/uploads` не коммитятся. Эти runtime artifacts создаются локально после API/batch processing и игнорируются Git.

## Что умеет baseline

- принимает документы через FastAPI или пакетную CLI-обработку;
- поддерживает `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`;
- поддерживает standalone `jpg`/`jpeg`/`png` как optional local OCR baseline: при наличии локального OCR engine текст может быть извлечен, при отсутствии сохраняется metadata-only OCR-candidate поведение;
- извлекает текст, таблицы, базовые метаданные и факт наличия изображений;
- строит `StructuredDocument` JSON с разделами, блоками, таблицами, изображениями и chunks;
- сохраняет результаты локально в `storage/`;
- строит локальный lexical index и дает source-backed `search` / extractive `ask` по уже обработанному корпусу.

Это не full RAG/LLM-продукт: LLM generation, summarization, semantic/vector search, embeddings/vector DB, scanned PDF OCR, embedded OCR inside DOCX/PDF и table analytics не являются реализованными возможностями.

## Быстрый старт

```powershell
conda run -n etl_env python -m pip install -e .[dev]
conda run -n etl_env uvicorn app.main:app --reload
```

Проверка API:

```powershell
curl http://127.0.0.1:8000/health
```

## Архитектура и pipeline

```text
intake -> extractor -> StructuredDocument JSON -> blocks/sections/tables/images -> chunks -> index/search/ask/eval
```

- `app/api` - FastAPI endpoints;
- `app/pipeline` - extract / transform / load;
- `app/storage` - файловое хранилище артефактов;
- `app/search` - локальный lexical retrieval по обработанным документам;
- `scripts` - CLI для batch/demo/audit/evaluation/inspection workflows;
- `tests` - regression baseline.

## Локальный API

```powershell
conda run -n etl_env uvicorn app.main:app --reload
```

Core endpoints:

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

`/api/v1/ask` возвращает source-backed evidence snippets. Если в корпусе нет ответа, сервис возвращает `нет информации в корпусе`. Это extractive/source-backed path, а не LLM answer synthesis.

## Sample processing, index и demo

В clear checkout meaningful demo/search требует сначала создать локальный sample corpus:

```powershell
conda run -n etl_env python -m scripts.batch_process --input-dir first_test_data
conda run -n etl_env python -m scripts.rebuild_corpus
conda run -n etl_env python -m scripts.demo_search --query "экология проект"
conda run -n etl_env python -m scripts.demo_customer_flow
```

`first_test_data` - sample input corpus в репозитории. `storage/index`, `storage/results` и `storage/uploads` - generated runtime output; они не являются baseline и не коммитятся.

Для ручной inspection/handoff проверки одного файла без загрязнения production `storage/`:

```powershell
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\file.docx"
```

По умолчанию inspector использует temporary workspace под `.runtime_eval`.

## Configuration

Настройки можно задавать через environment variables. Пример находится в `.env.example`.

| Variable | Example/default | Meaning |
| --- | --- | --- |
| `ETL_STORAGE_DIR` | `storage` | Корневой каталог runtime storage для uploads/results/index. |
| `ETL_ENABLE_OCR` | `false` | Включает optional local OCR path там, где доступен OCR engine. Не гарантирует наличие Tesseract. |
| `ETL_API_PREFIX` | `/api/v1` | Prefix для API routes. |

## Docker

В репозитории есть `Dockerfile`; `docker-compose.yml` отсутствует и не обязателен для baseline-запуска.

```powershell
docker build -t etl-service .
docker run --rm -p 8000:8000 etl-service
```

Если нужно сохранить результаты обработки между запусками контейнера, монтируйте volume для `storage/`:

```powershell
docker run --rm -p 8000:8000 -v ${PWD}\storage:/app/storage etl-service
```

`storage/` внутри контейнера - generated runtime output. Docker baseline не обещает OCR: standalone image OCR остается optional и зависит от наличия Tesseract/language packs в конкретном image/environment.

## Formats

Поддержанные baseline-форматы:

- documents: `pdf`, `doc`, `docx`, `rtf`, `txt`;
- spreadsheets: `xlsx`, `xls`;
- standalone OCR-candidate images: `jpg`, `jpeg`, `png`.

`xlsx` и `xls` извлекают таблицы, сохраняют их в JSON и дают row/table context для lexical retrieval. Advanced Excel semantics вроде formulas, macros, styles, merged cells и hidden-sheet behavior остаются вне scope.

`doc` baseline зависит от локального LibreOffice (`soffice`) для конвертации в `docx`, если он доступен.

Неподдерживаемые image-like formats: `HEIC`, `HEIF`, `TIFF`, `TIF`, `BMP`, `WEBP`.

## OCR

OCR для standalone `jpg`/`jpeg`/`png` является optional local baseline. Если локальный OCR engine недоступен, упал или вернул пустой/подозрительный результат, сервис сохраняет metadata/warning вместо того, чтобы молча выдавать плохой текст как quality baseline.

Проверка engine/language packs:

```powershell
conda run -n etl_env python -m scripts.check_ocr
```

Read-only OCR smoke/eval:

```powershell
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path .runtime_eval\ocr_smoke_report.json --language rus+eng
```

Scanned PDF OCR, embedded OCR inside DOCX/PDF, layout/table OCR и external/proprietary OCR API не реализованы.

## Evaluation и handoff scripts

Read-only workflows для проверки текущего baseline:

```powershell
conda run -n etl_env python -m scripts.audit_corpus
conda run -n etl_env python -m scripts.audit_rag_chunks --max-documents 1 --max-chunks-per-document 5
conda run -n etl_env python -m scripts.extract_requirements
conda run -n etl_env python -m scripts.evaluate_tables
```

Эти scripts показывают diagnostics/source-backed candidates и не являются LLM generation, semantic retrieval, full RAG, table analytics или legal/compliance guarantee.

## Limitations и future work

- Нет full RAG.
- Нет LLM generation / answer synthesis / summarization.
- Нет semantic retrieval, reranking, embeddings или vector DB.
- Нет scanned PDF OCR.
- Нет embedded OCR inside DOCX/PDF.
- Нет layout/table OCR.
- Нет SQL/table analytics или automatic calculations.
- Нет production UI.
- Optional OCR зависит от локального Tesseract и language packs.
- Existing processed JSON не мигрируется автоматически после splitter/chunk improvements.
- External QA source matching может быть ambiguous/missing; это требует review, а не автоматического выбора первого файла.

Будущая интеграция с RAG/LLM должна использовать текущий результат как ETL/RAG-readiness baseline: structured documents, chunks, table context, source/citation metadata и честные diagnostics.

## Документация

- `docs/project/OPERATION_GUIDE.md` - эксплуатационный маршрут, demo flow, temporary workspace policy и cleanup.
- `docs/project/METRICS_AND_ACCEPTANCE.md` - метрики качества и final acceptance gates для ETL/RAG-readiness baseline.
- `docs/project/FINAL_DELIVERY_CHECKLIST.md` - финальный verification/cleanup checklist перед физической копией проекта.
- `experiments/README.md` - воспроизводимые scripts/evaluation workflows без notebooks, external dataset copies или generated report artifacts.

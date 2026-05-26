# ETL Service

Локальный ETL-микросервис для структурированной обработки документов, lexical retrieval и source-backed evidence extraction.

ETL Service — FastAPI-сервис для локальной обработки документов и подготовки структурированных данных для retrieval workflows. Он извлекает текст, таблицы, базовые метаданные и сведения об изображениях, сохраняет результат в `StructuredDocument` JSON и строит локальный lexical index по обработанному корпусу.

Runtime-результаты создаются локально в `storage/` и не входят в репозиторий.
`first_test_data/` содержит только минимальные synthetic/generic sample files; реальные, customer или customer-adjacent датасеты должны храниться вне репозитория.

## Быстрый старт через Docker

Собрать и запустить API:

```powershell
docker build -t etl-service .
docker run --rm -p 8000:8000 etl-service
```

Проверить сервис:

```powershell
curl http://127.0.0.1:8000/health
```

Если нужно сохранять результаты обработки между запусками контейнера:

```powershell
docker run --rm -p 8000:8000 -v ${PWD}\storage:/app/storage etl-service
```

`storage/index`, `storage/results` и `storage/uploads` являются generated runtime output и должны оставаться вне Git.

## Локальная установка

Локальный запуск полезен для разработки, тестов и CLI workflow. Короткий путь:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
uvicorn app.main:app --reload
```

Подробная установка, переменные окружения и команды обработки корпуса описаны в [docs/setup.md](docs/setup.md).

## Возможности

* API для обработки документов, просмотра корпуса, лексического поиска и extractive source-backed ask.
* Поддержка `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`.
* Опциональный OCR-путь для standalone `jpg`, `jpeg`, `png`, если локальный OCR engine доступен.
* `StructuredDocument` JSON с sections, blocks, chunks, tables, image metadata и processing diagnostics.
* Локальный lexical index по уже обработанным документам.
* Минимальный synthetic/generic sample corpus в `first_test_data/`.
* Optional read-only `ETL_RULES_CONFIG_PATH` для deterministic category terms в `/api/v1/corpus/requirements` и `/api/v1/corpus/tables`.

## Результат обработки

После ingest сервис сохраняет:

* structured JSON (`StructuredDocument`);
* chunks для retrieval;
* table metadata;
* image metadata;
* lexical corpus index;
* source-backed evidence для search/ask.

Generated runtime output хранится локально в `storage/`.

## API

Основные endpoints:

* `GET /health`
* `POST /api/v1/documents/process`
* `GET /api/v1/documents`
* `GET /api/v1/documents/{document_id}`
* `POST /api/v1/search`
* `POST /api/v1/ask`
* `GET /api/v1/corpus/stats`
* `POST /api/v1/corpus/reindex`
* `GET /api/v1/corpus/manifest`
* `GET /api/v1/corpus/requirements`
* `GET /api/v1/corpus/tables`

`/api/v1/ask` возвращает extractive evidence из обработанного корпуса. Если ответ не найден, сервис возвращает явный no-information response вместо неподтвержденной генерации текста.

Category terms для `/api/v1/corpus/requirements` и `/api/v1/corpus/tables` можно расширить или заменить через optional read-only JSON config (`ETL_RULES_CONFIG_PATH`, пример: `config/rules.example.json`). Это deterministic term config, а не LLM, не generic rule engine и не runtime management endpoint.

## Ограничения

Это не full RAG и не LLM-продукт.

* Нет LLM generation, answer synthesis или summarization.
* Нет semantic search, vector search, embeddings, reranking или vector DB.
* Нет OCR для scanned PDF.
* Нет embedded OCR внутри DOCX или PDF.
* Нет table analytics, SQL-like QA или автоматических расчетов.
* OCR для standalone images зависит от локального Tesseract и language packs.
* Нет API/UI для runtime управления rules config.

## Архитектура

```text
documents
    ↓
extractors
    ↓
StructuredDocument JSON
    ↓
chunks + metadata
    ↓
lexical index
    ↓
search / ask
```

* `app/api` — FastAPI routes.
* `app/pipeline` — extraction и transformation.
* `app/storage` — filesystem-backed storage helpers.
* `app/search` — локальный lexical index и retrieval path.
* `scripts` — processing, rebuild, audit и inspection utilities.

## Проверка качества

Базовая проверка локального checkout:

```powershell
python -m pytest -q
python -m scripts.batch_process --input-dir first_test_data
```

Содержательный search и ask требуют предварительной локальной обработки корпуса.

Подробные команды и workflow:

* [docs/setup.md](docs/setup.md)
* [docs/api_and_workflows.md](docs/api_and_workflows.md)

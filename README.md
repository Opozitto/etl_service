# ETL Service

Автономный ETL-микросервис для извлечения структуры из документов и подготовки данных для последующей обработки и задач поиска.

## Что умеет baseline

- принимает документы через API или пакетную CLI-обработку
- поддерживает `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`
- `jpg`/`png` фиксирует как наличие изображений без OCR
- извлекает текст, таблицы, базовые метаданные и факт наличия изображений
- строит структурированный JSON с разделами, блоками и таблицами
- сохраняет результаты локально в `storage/`
- индексирует все обработанные документы и позволяет делать простой поиск по корпусу
- `XLS` остаётся известным ограничением и не считается подтверждённым baseline-форматом

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
Если в корпусе нет ответа, сервис возвращает `нет информации в корпусе`.

## Batch обработка директории

```bash
conda run -n etl_env python -m scripts.batch_process --input-dir first_test_data
```

С отчётом:

```bash
conda run -n etl_env python -m scripts.batch_process --input-dir first_test_data --report-path storage/index/last_batch_report.json
```

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

## Поддержка DOC

Для старых файлов `DOC` baseline использует локальный `LibreOffice` (`soffice`) и конвертирует документ в `DOCX` перед извлечением. Внешние API не используются.

# API workflow

API доступен после запуска сервиса на `http://127.0.0.1:8000`. Подробная установка и запуск описаны в [setup.md](setup.md).

Этот walkthrough показывает ручной сценарий проверки ETL Service через HTTP API. Search и ask работают по уже обработанному локальному корпусу и не являются LLM/full RAG.
Requirement/table category terms можно настроить через optional read-only `ETL_RULES_CONFIG_PATH`; это deterministic term config для `/api/v1/corpus/requirements` и `/api/v1/corpus/tables`, без runtime management endpoint.

## Рекомендуемый ручной сценарий

1. `GET /health` — проверить, что сервис жив.
2. `POST /api/v1/documents/process` — загрузить и обработать документ.
3. `GET /api/v1/documents` — увидеть обработанные документы.
4. `GET /api/v1/documents/{document_id}` — открыть structured JSON конкретного документа.
5. `POST /api/v1/corpus/reindex` — пересобрать lexical index.
6. `POST /api/v1/search` — проверить top chunks/evidence.
7. `POST /api/v1/ask` — проверить extractive source-backed answer.
8. `GET /api/v1/corpus/stats` и `GET /api/v1/corpus/manifest` — посмотреть состояние корпуса.
9. `GET /api/v1/corpus/requirements` и `GET /api/v1/corpus/tables` — посмотреть deterministic candidates/evidence.

## GET /health

Назначение: быстрая проверка, что API запущен и отвечает.

```powershell
curl.exe http://127.0.0.1:8000/health
```

Что смотреть в ответе: успешный HTTP response и health/status payload. Если endpoint не отвечает, сначала проверьте, что `uvicorn` или Docker container запущен и порт `8000` доступен.

## POST /api/v1/documents/process

Назначение: загрузить один документ, извлечь структуру и сохранить результат в локальный corpus storage. Endpoint принимает multipart form-data с полем `file`.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/documents/process `
  -F "file=@first_test_data/synthetic_requirements.txt"
```

Что смотреть в ответе: объект `document` с `metadata.document_id`, `source.filename`, `sections`, `blocks`, `tables`, `images`, `chunks`, `processing_info` и `artifacts`. Для дальнейших запросов сохраните `metadata.document_id`.

## GET /api/v1/documents

Назначение: получить короткий список документов, уже обработанных в локальном corpus.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/documents
```

Что смотреть в ответе: `document_id`, `filename`, `title`, `processed_at` и `page_count`. Если список пустой, сначала обработайте документ через `/api/v1/documents/process` или CLI batch flow.

## GET /api/v1/documents/{document_id}

Назначение: открыть полный structured JSON конкретного документа.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/documents/<document_id>
```

Что смотреть в ответе: полную структуру `StructuredDocument`, включая sections/blocks/tables/chunks и warnings в `processing_info`. Это основной объект для проверки качества extraction и chunking.

## POST /api/v1/corpus/reindex

Назначение: пересобрать локальный lexical index по JSON-файлам из `storage/results`. Полезно после batch processing или ручных изменений локального corpus storage.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/corpus/reindex
```

Что смотреть в ответе: `status`, `document_count`, `chunk_count`, `updated_at`. Если `document_count` или `chunk_count` равны нулю, проверьте наличие processed JSON в `storage/results`.

## POST /api/v1/search

Назначение: найти релевантные chunks/evidence в локальном lexical index. Это keyword/lexical retrieval, не semantic/vector search.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/search `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"экология проект\",\"top_k\":5}"
```

Что смотреть в ответе: массив `hits` с `score`, `filename`, `chunk_id`, `section_title`, `page_start/page_end`, `snippet` и source metadata. Хороший результат должен показывать понятный фрагмент источника, а не сгенерированный ответ.

## POST /api/v1/ask

Назначение: получить extractive source-backed answer на основе найденных chunks. Endpoint не вызывает LLM и не синтезирует ответ за пределами найденного корпуса.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"Что сказано про экологию проекта?\",\"top_k\":5,\"max_sentences\":4}"
```

Что смотреть в ответе: `answer`, `sources`, `hits` и `strategy`. `sources` должны указывать на документы/chunks, из которых взят ответ. Если информации нет, ожидайте явный no-information response вместо неподтвержденной генерации.

## GET /api/v1/corpus/stats

Назначение: быстро посмотреть размер и состояние локального corpus index.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/corpus/stats
```

Что смотреть в ответе: `document_count`, `chunk_count`, `avg_chunk_length`, `manifest_record_count`, `updated_at`. Эти поля помогают понять, есть ли обработанный корпус и построен ли index.

## GET /api/v1/corpus/manifest

Назначение: посмотреть manifest обработанных документов.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/corpus/manifest
```

Что смотреть в ответе: `filename`, `checksum_sha256`, `extractor`, `status`, `processed_at`, `warnings`. Manifest удобен для проверки, какие source-файлы реально попали в corpus.

## GET /api/v1/corpus/requirements

Назначение: получить deterministic requirement-like candidates по обработанному корпусу. Это эвристический source-backed report, не юридическая или LLM-оценка.

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/corpus/requirements?min_score=0.45"
```

Что смотреть в ответе: `summary`, `candidates`, `category`, `score`, `matched_terms`, `snippet` и source location fields. Используйте результат как навигацию к возможным source fragments.

Category detection использует built-in deterministic terms, которые можно расширить или заменить через optional read-only JSON config (`config/rules.example.json`). Некорректный или отсутствующий config безопасно оставляет defaults.

## GET /api/v1/corpus/tables

Назначение: посмотреть deterministic table evidence candidates по обработанным таблицам и table-like fragments. Это не table analytics и не automatic calculations.

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/corpus/tables?min_score=0.25"
```

Что смотреть в ответе: `summary`, `tables`, `headers`, `preview_rows`, `category`, `score`, `matched_terms`, `snippet`. Результат помогает проверить, какие таблицы и строки доступны для source-backed retrieval.

Table category detection использует deterministic terms. Optional config поддерживает только известные table categories и не externalizes structural table heuristics, service table detection, OCR gates или search tokenization.

## Runtime files

API и CLI создают локальные runtime files:

- `storage/uploads` — сохраненные source-файлы при service processing.
- `storage/results` — `StructuredDocument` JSON по одному `<document_id>.json` на документ.
- `storage/index` — lexical index и ingestion manifest.

Эти файлы являются generated output, зависят от локального запуска и не коммитятся.

`first_test_data/` в repo является минимальным synthetic/generic sample corpus. Реальные/customer datasets должны храниться вне репозитория.

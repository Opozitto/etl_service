# Руководство по запуску

Это практическое руководство для ручной проверки ETL Service: запуск API, обработка документа, просмотр результатов, search/ask, rebuild index и проверка OCR.

## Быстрый старт через Docker

Собрать image:

```powershell
docker build -t etl-service .
```

Запустить API:

```powershell
docker run --rm -p 8000:8000 etl-service
```

Проверить сервис:

```powershell
curl http://127.0.0.1:8000/health
```

Если нужно сохранять runtime output между запусками контейнера:

```powershell
docker run --rm -p 8000:8000 -v ${PWD}\storage:/app/storage etl-service
```

## Локальная установка

Создать virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Установить проект:

```powershell
python -m pip install -e .[dev]
```

Запустить API:

```powershell
uvicorn app.main:app --reload
```

API будет доступен на `http://127.0.0.1:8000`.

## API health check

Проверить, что приложение запущено:

```powershell
curl http://127.0.0.1:8000/health
```

PowerShell-вариант:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

## Обработка документа через API

Endpoint `POST /api/v1/documents/process` принимает multipart upload с полем `file`.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/documents/process `
  -F "file=@first_test_data/test.docx"
```

PowerShell-вариант:

```powershell
$form = @{ file = Get-Item "first_test_data\test.docx" }
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/documents/process -Method Post -Form $form
```

В ответе вернется `document` со структурой `StructuredDocument`: metadata, source, sections, blocks, tables, images, chunks, processing_info и artifacts.

## Просмотр документов

Список обработанных документов:

```powershell
curl http://127.0.0.1:8000/api/v1/documents
```

Получить конкретный документ:

```powershell
curl http://127.0.0.1:8000/api/v1/documents/<document_id>
```

Статистика корпуса:

```powershell
curl http://127.0.0.1:8000/api/v1/corpus/stats
```

Manifest корпуса:

```powershell
curl http://127.0.0.1:8000/api/v1/corpus/manifest
```

## Search

Search работает по локальному lexical index, который строится после обработки документов.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/search `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"экология проект\",\"top_k\":5}"
```

PowerShell-вариант:

```powershell
$body = @{ query = "экология проект"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/search -Method Post -ContentType "application/json" -Body $body
```

Ответ содержит `hits`: score, filename, chunk_id, section/page context, snippet и source metadata.

## Ask

Ask возвращает extractive source-backed answer по найденным фрагментам. Это не LLM generation.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"Что сказано про экологию проекта?\",\"top_k\":5,\"max_sentences\":4}"
```

PowerShell-вариант:

```powershell
$body = @{
  question = "Что сказано про экологию проекта?"
  top_k = 5
  max_sentences = 4
} | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/ask -Method Post -ContentType "application/json" -Body $body
```

Если подходящих источников нет, сервис возвращает явный no-information response.

## Rebuild index

Если JSON-файлы уже есть в `storage/results`, но index нужно пересобрать:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/corpus/reindex
```

CLI-вариант:

```powershell
python -m scripts.rebuild_corpus
```

## Manual workflow через API

Минимальная ручная проверка:

1. Запустить API.
2. Проверить `/health`.
3. Отправить файл в `/api/v1/documents/process`.
4. Проверить `/api/v1/documents`.
5. Выполнить `/api/v1/search`.
6. Выполнить `/api/v1/ask`.
7. При необходимости пересобрать index через `/api/v1/corpus/reindex`.

## Обработка sample corpus через CLI

CLI полезен для быстрой локальной подготовки корпуса:

```powershell
python -m scripts.batch_process --input-dir first_test_data
python -m scripts.rebuild_corpus
```

Demo utilities можно использовать как дополнительные smoke checks:

```powershell
python -m scripts.demo_search --query "экология проект"
python -m scripts.demo_customer_flow
```

Они не являются основным API workflow; это удобные локальные wrappers.

## Inspect одного файла

Проверить структуру одного файла без добавления его в основной corpus flow:

```powershell
python -m scripts.inspect_document_structure --input-path "D:\path\file.docx"
```

Сохранить markdown/json report в temporary output:

```powershell
python -m scripts.inspect_document_structure --input-path "D:\path\file.docx" `
  --output-path .runtime_eval\inspect_report.md `
  --json-report-path .runtime_eval\inspect_report.json `
  --clean-workspace
```

## Где появляются результаты

По умолчанию используется `ETL_STORAGE_DIR=storage`.

- `storage/uploads` - сохраненные source-файлы при service processing.
- `storage/results` - обработанные `StructuredDocument` JSON, по одному `<document_id>.json` на документ.
- `storage/index` - локальный lexical index и manifest.
- `.runtime_eval` - временные отчеты и workspace для inspect/evaluation scripts, если указаны такие paths.

`storage/results/<document_id>.json` содержит:

- `metadata`: id, title, processed_at, counts.
- `source`: filename, extension, checksum.
- `sections`, `blocks`, `tables`, `images`.
- `chunks`: фрагменты для retrieval.
- `processing_info`: extractor, warnings, feature flags.
- `artifacts`: путь к result JSON.

Runtime outputs являются локальными generated files и не должны коммититься.

## OCR

Установить OCR-зависимости Python:

```powershell
python -m pip install -e .[dev,ocr]
```

Проверить доступность OCR engine и language packs:

```powershell
python -m scripts.check_ocr
```

Запустить OCR smoke для sample corpus:

```powershell
python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path .runtime_eval\ocr_smoke_report.json --language rus+eng
```

OCR поддерживается только как optional path для standalone `jpg`, `jpeg`, `png`. Scanned PDF OCR и embedded OCR внутри DOCX/PDF не входят в текущий scope.

## Переменные окружения

В репозитории есть `.env.example`:

```text
ETL_STORAGE_DIR=storage
ETL_ENABLE_OCR=false
ETL_API_PREFIX=/api/v1
```

Переменные:

- `ETL_STORAGE_DIR`: корневой каталог для generated uploads, results и index files.
- `ETL_ENABLE_OCR`: включает optional OCR path, если зависимости и OCR engine доступны.
- `ETL_API_PREFIX`: prefix для API routes.

## Тесты

Локальная regression-проверка:

```powershell
python -m pytest -q
```

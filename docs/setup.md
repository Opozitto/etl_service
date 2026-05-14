# Руководство по запуску

Это руководство описывает Docker-запуск, локальную установку, API checks и базовые CLI workflow для ETL Service.

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

Сохранять generated runtime output между запусками:

```powershell
docker run --rm -p 8000:8000 -v ${PWD}\storage:/app/storage etl-service
```

Примонтированный `storage/` является локальным generated output. Не коммитьте `storage/index`, `storage/results` и `storage/uploads`.

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

Проверить API:

```powershell
curl http://127.0.0.1:8000/health
```

Запустить tests:

```powershell
python -m pytest -q
```

## OCR опционально

Установить Python-зависимости для OCR:

```powershell
python -m pip install -e .[dev,ocr]
```

OCR также требует локальный OCR engine, например Tesseract, и нужные language packs. Если engine недоступен, OCR-зависимые команды могут сообщить, что OCR недоступен, или перейти в metadata-only behavior.

Проверить OCR setup:

```powershell
python -m scripts.check_ocr
```

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

## Processing, demo и search

Репозиторий не содержит prebuilt index. Для содержательного search и ask сначала нужна локальная обработка документов.

Обработать sample corpus:

```powershell
python -m scripts.batch_process --input-dir first_test_data
```

Пересобрать локальный index:

```powershell
python -m scripts.rebuild_corpus
```

Запустить search demo:

```powershell
python -m scripts.demo_search --query "экология проект"
```

Запустить компактный demo flow:

```powershell
python -m scripts.demo_customer_flow
```

Проверить структуру одного файла без добавления его в sample corpus:

```powershell
python -m scripts.inspect_document_structure --input-path "D:\path\file.docx"
```

## Runtime output

Локальная обработка пишет generated output в ignored paths:

- `storage/index`
- `storage/results`
- `storage/uploads`
- `.runtime_eval`

Эти файлы не являются частью исходного репозитория.

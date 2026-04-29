# WORKLOG

## done

- Stage 3 закрыт.
- Stage 4 подтверждён через `tests/test_api.py`.
- Contract tests для JSON/output contract добавлены и локально проходят в `etl_env`.
- Подтверждённый regression-check без активации окружения:
  - `conda run -n etl_env python -m pytest -q`
  - результат: `13 passed in 12.75s`
- Подтверждённый regression-check в активированном окружении:
  - `conda activate etl_env`
  - `python -m pytest -q`
  - ранее подтверждённый результат: `13 passed`
- Stage 3 contract tests покрывают:
  - round-trip `StructuredDocument` JSON;
  - save/load `CorpusIndex`;
  - save/load `CorpusManifest`;
  - API shape для process/list/detail document;
  - `txt` extractor fallback encoding через `tmp_path`.
- Проверка API Stage 4:
  - `conda run -n etl_env python -m pytest -q tests/test_api.py`
  - результат: `4 passed in 12.89s`
- Поток API Stage 4 подтверждён:
  - healthcheck
  - upload/process
  - get/list documents
  - search
  - ask
  - corpus stats
  - corpus reindex
  - corpus manifest
- Retrieval proof/demo Stage 5 подтверждён:
  - `conda run -n etl_env python -m scripts.rebuild_corpus`
  - `conda run -n etl_env python -m scripts.demo_search --query "экология проект"`
  - результат: `rebuild_corpus` пересобрал индекс корпуса, а `demo_search` вернул ненулевые top hits по запросу `экология проект`
  - ask остаётся подтверждённым на уровне API через Stage 4 и `tests/test_api.py`
- Выравнивание README/demo с baseline Stage 6 подтверждено:
  - `README.md` выровнен с текущими заявлениями baseline
  - команды retrieval demo используют `conda run -n etl_env`
  - OCR задокументирован как вне текущего baseline
  - `jpg`/`png` задокументированы только как фиксация наличия изображений
  - `XLS` задокументирован как известное ограничение, а не как подтверждённый baseline-формат
- Stage 7 закрыт.
  - commit: `bbe0b90`
  - расширен batch/evaluation report в `scripts/batch_process.py`
  - добавлен `report_version: "stage7_batch_report_v1"`
  - добавлен summary block
  - добавлены item-level metrics
  - добавлены тесты в `tests/test_batch_process.py`
  - локальные проверки:
    - `python -m pytest -q tests\test_batch_process.py` -> `1 passed`
    - `python -m pytest -q tests\test_contracts.py` -> `4 passed`
- Stage 8 закрыт.
  - commit: `c08a66a`
  - добавлен read-only corpus quality audit в `scripts/audit_corpus.py`
  - добавлены тесты в `tests/test_audit_corpus.py`
  - локальные проверки:
    - `python -m pytest -q tests\test_audit_corpus.py` -> `2 passed`
    - `python -m py_compile scripts\audit_corpus.py tests\test_audit_corpus.py` -> `OK`

## next

- Stage 9 — retrieval quality mini-evaluation.

## risks

- `.XLS` файл в `first_test_data` по-прежнему не считается подтверждённым baseline-форматом.
- Полный `pytest` внутри Codex sandbox на Windows может падать на `PermissionError` в pytest temp/`tmp_path`, хотя локальный запуск в `etl_env` проходит.

## decisions

- `python -m pytest -q` без активации `etl_env` не является валидной проверкой проекта, потому что использует base Anaconda и может падать из-за отсутствующих зависимостей, например `httpx`.
- Источник истины для `pytest`-регрессии:
  - `conda run -n etl_env python -m pytest -q`
  - или `python -m pytest -q` только после `conda activate etl_env`
- Ограничение Codex sandbox на Windows трактуется как локальное ограничение окружения и ACL, а не как ошибка проекта.
- Stage 3 считается закрытым без workaround-ов в коде и тестах.

## open questions

- `не подтверждено`: нужно ли отдельно документировать `.XLS` как legacy input вне baseline Stage 2.

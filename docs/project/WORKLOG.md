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
- Поток API Stage 4 подтверждён `tests/test_api.py`; production-код и тесты на этом шаге не менялись.
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
- Финальная локальная baseline-регрессия пользователя в `etl_env` подтверждена:
  - `python -m pytest -q`
  - результат: `13 passed in 13.22s`
  - `python -m scripts.rebuild_corpus`
  - результат: `Rebuilt corpus index: documents=12 chunks=2836 updated_at=2026-04-29T10:34:49.318315`
  - `python -m scripts.demo_search --query "экология проект"`
  - результат: 5 top hits; первый hit: `file=test.docx score=11.6432`

## next

- Stage 1–6 baseline подтверждён; следующий шаг — упаковка и передача результата заказчику, без кодовых изменений.

## risks

- `.XLS` файл в `first_test_data` по-прежнему не считается подтвержденным baseline-форматом.
- Полный `pytest` внутри Codex sandbox на Windows может падать на `PermissionError` в `pytest` temp/`tmp_path`, хотя локальный запуск в `etl_env` проходит.

## decisions

- `python -m pytest -q` без активации `etl_env` не является валидной проверкой проекта, потому что использует base Anaconda и может падать из-за отсутствующих зависимостей, например `httpx`.
- Источник истины для `pytest`-регрессии:
  - `conda run -n etl_env python -m pytest -q`
  - или `python -m pytest -q` только после `conda activate etl_env`
- Ограничение Codex sandbox на Windows трактуется как локальное ограничение окружения и ACL, а не как ошибка проекта.
- Stage 3 считается закрытым без workaround-ов в коде и тестах.

## open questions

- `не подтверждено`: нужно ли отдельно документировать `.XLS` как legacy input вне baseline Stage 2.

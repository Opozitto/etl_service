# WORKLOG

## done

- Stage 3 closed.
- Stage 4 confirmed through `tests/test_api.py`.
- Stage 5 retrieval proof/demo confirmed.
- Stage 6 README/demo alignment confirmed against the current baseline.
- Stage 7 closed as the batch/evaluation reporting layer.
- Stage 8 closed as the read-only corpus quality audit.
- Stage 9 closed as the retrieval quality mini-evaluation.
- After Stage 9, a roadmap realignment was performed against the extended customer brief.
- Stage 10 customer scenarios and evaluation set created as a docs-only artifact.
- Stage 11 closed as the source-backed ask response alignment.
- Stage 12 partial: explicit unsupported image format contract added for known image-like formats outside `jpg`/`jpeg`/`png`, with user-facing wording localized to Russian.
- Stage 12.2 completed as standalone `jpg`/`jpeg`/`png` image intake smoke/evaluation without OCR.
- Stage 12 closed with API smoke/evaluation for standalone image intake and documentation closure.
- Stage 12 follow-up: added manual image intake sample files `first_test_data/Справка (таблица).jpg` and `first_test_data/Справка (таблица).png`.
- Code/tests/OCR/dependencies were unchanged in the sample-files follow-up.
- Commits:
  - `6997d98` `Add unsupported image format contract`
  - `83b741b` `Localize unsupported image format message`
  - `26199bd` `Add image intake smoke contract`
  - `0a57c48` `Close Stage 12 image intake contract`
- Checks:
  - `python -m pytest -q tests\test_extractors.py -k "image or registry"` -> Stage 12.2 contract check;
  - `python -m py_compile tests\test_extractors.py` -> OK.
- Commit: `1a02af5` `Add source-backed ask response`.
- Checks:
  - `python -m pytest -q tests\test_api.py` -> 4 passed
  - `python -m pytest -q tests\test_search.py` -> 3 passed
  - `python -m py_compile app\schemas\api.py app\search\index.py tests\test_api.py` -> OK
- Storage changes after `test_api` were cleaned before commit.
- `git status --short` after commit was clean.

## next

- Stage 19A: retrieval evaluation v2 / table-aware evaluation set.
- Stage 19B: OCR intake spike for `jpg` / `png` scans.
- Stage 19C: summarization / draft generation spike.
- Stage 19D: prototype API demo packaging.

## alignment

- Stage 7–9 теперь считаются quality/evaluation foundation проекта.
- Эта основа покрывает часть брифа про оценку качества решений.
- Следующая фаза — pilot AI-service track для экологов-проектировщиков, а не заявление о том, что OCR, RAG или LLM generation уже готовы.

## risks

- `.XLS` и `.XLSX` поддерживаются как baseline spreadsheet inputs.
- Spreadsheet retrieval остаётся lexical; улучшение даёт row-level context, а не table-aware analytics.
- OCR не реализован.
- `HEIC` / `HEIF` / `TIFF` / `TIF` / `BMP` / `WEBP` остаются неподдерживаемыми.
- LLM / RAG / generation не реализованы.
- Полный `pytest` внутри Codex sandbox на Windows всё ещё может упираться в `PermissionError` в pytest temp / `tmp_path`, хотя локальный `etl_env` запуск работает.
- `PermissionError` в Codex sandbox остаётся ограничением окружения, а не дефектом проекта.

## decisions

- `python -m pytest -q` без активации `etl_env` не считается валидной проверкой проекта, потому что может использовать base Anaconda и не видеть зависимости вроде `httpx`.
- Источник истины для pytest-регрессии остаётся таким:
  - `conda run -n etl_env python -m pytest -q`
  - или `python -m pytest -q` только после `conda activate etl_env`
- Ограничения Codex sandbox по ACL на Windows считаются ограничением окружения, а не поводом менять код или тесты.
- Stage 3 остаётся закрытым без workaround-изменений в коде или тестах.

## open questions

- `не подтверждено`: нужен ли future work для true table-aware reasoning beyond the current flattened retrieval baseline.

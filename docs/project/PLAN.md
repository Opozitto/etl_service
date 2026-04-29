# PLAN

## Stage 1. Зафиксировать smoke/regression проверки

- Цель: определить минимальные проверки, которые защищают подтверждённый baseline от регрессий.
- Подзадачи:
  - зафиксировать команду установки зависимостей;
  - зафиксировать `pytest` как основную regression-проверку;
  - зафиксировать CLI-команды, которые считаются baseline smoke.
- Артефакты:
  - `README.md` как текущий источник команд;
  - `WORKLOG.md` как журнал прогонов.
- Команды проверки:
```powershell
conda run -n etl_env python -m pip install -e .[dev]
conda run -n etl_env python -m pytest -q
conda run -n etl_env python -m scripts.rebuild_corpus
conda run -n etl_env python -m scripts.demo_search --query "экология проект"
```
- Критерий завершения:
  - команды установки и smoke/regression подтверждены в локальном окружении.

## Stage 2. Проверить ETL на поддерживаемых форматах

- Цель: подтвердить, что текущий ETL baseline работает на поддерживаемых форматах, уже присутствующих в репозитории.
- Подзадачи:
  - подтвердить `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`;
  - подтвердить baseline image presence handling;
  - сопоставить поведение extractor'ов с тестами и сохранёнными результатами.
- Артефакты:
  - `app/pipeline/extractors/*`
  - `tests/test_extractors.py`
  - `storage/results/*`
- Команды проверки:
```powershell
conda run -n etl_env python -m pytest -q tests\test_extractors.py tests\test_structure.py
conda run -n etl_env python -m scripts.batch_process --input-dir first_test_data
```
- Критерий завершения:
  - каждый поддерживаемый формат обрабатывается без baseline-ошибок.

## Stage 3. Зафиксировать JSON/output contract

- Цель: сохранить стабильный контракт вывода для JSON документов, индекса корпуса и manifest.
- Подзадачи:
  - проверить `StructuredDocument` и API schemas;
  - проверить `corpus_index.json` и `ingestion_manifest.json`;
  - убедиться, что сохранённые данные и API-ответы совпадают по смыслу.
- Артефакты:
  - `app/schemas/document.py`
  - `app/schemas/api.py`
  - `storage/index/corpus_index.json`
  - `storage/index/ingestion_manifest.json`
- Команды проверки:
```powershell
conda run -n etl_env python -m pytest -q tests\test_api.py tests\test_search.py
conda run -n etl_env python -m scripts.rebuild_corpus
```
- Критерий завершения:
  - JSON output contract подтверждён и не расходится с кодом или сохранёнными данными.

## Stage 4. Подтвердить поток API

- Цель: убедиться, что основной HTTP-путь работает от загрузки до corpus endpoints.
- Подзадачи:
  - проверить `process`, `get/list documents`, `search`, `ask`, `corpus stats`, `corpus reindex` и `corpus manifest`;
  - согласовать поведение API с текущими тестами;
  - убедиться, что API не зависит от недокументированных шагов.
- Артефакты:
  - `app/api/routes/documents.py`
  - `app/main.py`
  - `tests/test_api.py`
- Команды проверки:
```powershell
conda run -n etl_env python -m pytest -q tests\test_api.py
```
- Критерий завершения:
  - поток API подтверждён тестами и соответствует текущему baseline.

## Stage 5. Подтвердить retrieval proof/demo

- Цель: сохранить минимальное, но рабочее доказательство поиска по локальному корпусу.
- Подзадачи:
  - проверить `rebuild_corpus` на существующем корпусе;
  - проверить `demo_search` на осмысленном запросе;
  - убедиться, что retrieval возвращает top hits из локального storage/index.
- Артефакты:
  - `app/search/index.py`
  - `app/search/store.py`
  - `scripts/rebuild_corpus.py`
  - `scripts/demo_search.py`
- Команды проверки:
```powershell
conda run -n etl_env python -m scripts.rebuild_corpus
conda run -n etl_env python -m scripts.demo_search --query "экология проект"
```
- Критерий завершения:
  - retrieval demo стабильно возвращает top results в локальном окружении.

## Stage 6. Финальная упаковка README/demo

- Цель: привести пользовательскую документацию и команды запуска к одному понятному baseline-пути.
- Подзадачи:
  - проверить README по фактическим командам;
  - уточнить порядок действий для нового участника;
  - убедиться, что README не обещает ничего, что baseline не подтверждает.
- Артефакты:
  - `README.md`
  - `WORKLOG.md`
- Команды проверки:
```powershell
conda run -n etl_env python -m pytest -q
conda run -n etl_env python -m scripts.rebuild_corpus
conda run -n etl_env python -m scripts.demo_search --query "экология проект"
```
- Критерий завершения:
  - README и demo flow отражают реальный baseline и ведут к подтверждённому результату.

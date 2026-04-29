# PLAN

Stage 1–6 are a closed baseline. Stage 7–9 are completed and form the local batch/evaluation foundation. The sections below keep the baseline history, align it with the customer brief, and define the next planned phases.

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

## Stage 7. Evaluation / batch reporting layer

- Цель: зафиксировать batch/evaluation layer, который даёт summary report по пакетной обработке.
- Подзадачи:
  - добавить `report_version: "stage7_batch_report_v1"`;
  - сохранить summary block для processed / duplicate / error;
  - зафиксировать item-level metrics по каждому файлу;
  - поддержать report output в `scripts/batch_process.py`.
- Артефакты:
  - `scripts/batch_process.py`
  - `tests/test_batch_process.py`
- Статус: completed.
- Рамка этапа:
  - OCR, semantic retrieval, RAG, vector DB и LLM generation не входят в Stage 7–9, если это не отдельный будущий этап.

## Stage 8. Corpus quality audit

- Цель: проверить качество corpus и формат данных без изменения production flow.
- Подзадачи:
  - оценить полноту и чистоту корпуса;
  - проверить duplicate/noise patterns и материалы с потерями метаданных;
  - зафиксировать ключевые метрики аудита.
- Артефакты:
  - `scripts/audit_corpus.py`
  - `tests/test_audit_corpus.py`
- Команды проверки:
```powershell
conda run -n etl_env python -m pytest -q tests\test_audit_corpus.py
conda run -n etl_env python -m py_compile scripts\audit_corpus.py tests\test_audit_corpus.py
```
- Статус: completed.

## Stage 9. Retrieval quality mini-evaluation

- Цель: сделать небольшой reproducible mini-eval для local retrieval quality.
- Подзадачи:
  - собрать small query set и expected hits;
  - сравнить baseline retrieval quality по queries / top-k;
  - зафиксировать воспроизводимый evaluation output.
- Статус: completed.
- Рамка этапа:
  - OCR, semantic retrieval, RAG, vector DB и LLM generation по-прежнему не входят в Stage 8–9.

## Customer brief alignment

- Цель: выровнять roadmap под расширенный бриф заказчика без переписывания текущего baseline и без обещаний уже не реализованных возможностей.
- Что уже подтверждено Stage 7–9:
  - batch/evaluation reporting layer;
  - read-only corpus quality audit;
  - retrieval quality mini-evaluation;
  - это покрывает часть брифа про «Оценка качества решений» и создаёт foundation для следующего пилотного AI-service track.
- Что не подтверждено и не должно декларироваться как готовое:
  - OCR;
  - semantic retrieval и полноценный RAG;
  - vector DB;
  - LLM generation / answer synthesis;
  - автоматическая генерация фрагментов документации.

## Stage 10. Customer scenarios and evaluation set

- Цель: зафиксировать пользовательские сценарии экологов-проектировщиков и сформировать evaluation set для пилотного AI-service track.
- Подзадачи:
  - описать типовые сценарии работы с исходными файлами клиента;
  - собрать список типовых вопросов и expected outputs;
  - определить acceptance criteria для поиска, извлечения, суммаризации и Q&A;
  - связать сценарии с доступными локальными источниками и метриками качества.
- Статус: completed.

## Stage 11. Ask / extractive QA proof with sources

- Цель: улучшить текущий `ask` как source-backed extractive QA без LLM generation.
- Подзадачи:
  - проверить текущий `ask` behavior;
  - зафиксировать answer provenance и source grounding;
  - ограничить scope до extractive proof, а не до генеративного ответа;
  - уточнить, какие ответы можно давать на базе существующего корпуса.
- Статус: completed.
- Фактический контракт `/api/v1/ask`:
  - `AskResponse` содержит `question`, `answer`, `sources`, `hits`, `strategy`;
  - `sources` — source-backed evidence snippets;
  - `hits` сохранён для обратной совместимости;
  - no-hit answer: `нет информации в корпусе`.

## Stage 12. OCR / image intake spike

- Статус: completed.
- Итог:
  - `jpg`/`jpeg`/`png` принимаются как standalone image input в metadata-only режиме;
  - OCR не реализован;
  - `HEIC`/`HEIF`/`TIFF`/`TIF`/`BMP`/`WEBP` остаются known unsupported image-like форматами с русским user-facing сообщением;
  - API smoke для `/api/v1/documents/process` покрыт тестом.

## Stage 12.2. Standalone image intake smoke/evaluation

- Цель: зафиксировать smoke/evaluation контракт для `jpg`/`jpeg`/`png` standalone image intake без OCR.
- Подтверждено:
  - `jpg`/`jpeg`/`png` принимаются как standalone image input;
  - OCR не запускается;
  - текст не извлекается;
  - image presence фиксируется через `image_count`, `images`, `blocks` и `processing_info.features`;
  - `HEIC`/`HEIF`/`TIFF`/`TIF`/`BMP`/`WEBP` остаются known unsupported image-like форматами.
- Статус: completed.

## Stage 13. XLS / tables / semi-structured input decision

- Цель: закрыть baseline decision по `XLS` и таблицам без расширения scope за пределы текущего ETL/search baseline.
- Подзадачи:
  - подтвердить, что `XLSX` поддерживается на текущем baseline-уровне;
  - зафиксировать, что table blocks/chunks из `XLSX` попадают в retrieval path;
  - явно оформить старый бинарный `XLS` как unsupported known spreadsheet format;
  - не обещать полноценную table-aware reasoning / analytics.
- Статус: completed.

## Stage 14. Summarization / draft generation spike

- Цель: после QA/OCR/eval проверить локальные или open-source варианты суммаризации и draft generation.
- Подзадачи:
  - сформировать небольшой proof-of-value scope;
  - не включать fine-tuning в roadmap как обещание;
  - рассматривать только локальные или open-source варианты, если они будут разрешены;
  - привязать выводы к качеству источников и ограничениям корпуса.
- Статус: planned.

## Stage 15. Prototype integration flow

- Цель: собрать демонстрационный flow `upload` / `process` / `audit` / `search` / `eval` / `ask`.
- Подзадачи:
  - связать подтверждённые части baseline и pilot track в один demo flow;
  - оставить audit/eval visible в прототипе;
  - не заявлять полноценный RAG или end-to-end generation до фактической реализации;
  - подготовить основу для рабочего прототипа сервиса для экологов-проектировщиков.
- Статус: planned.

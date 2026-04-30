# PLAN

Stage 1–6 are a closed baseline. Stage 7–9 are completed and form the local batch/evaluation foundation. Stage 10–17.1 are completed and documented below. Stage 18 is completed. Stage 19.0 is the delivery-first roadmap lock, Stage 20 is the optional local OCR baseline for standalone images, Stage 21 is the completed read-only OCR smoke evaluation layer, Stage 22 is the completed requirements extraction v1 layer, Stage 23 is the completed table evidence evaluation layer, Stage 24 is the completed read-only QA/retrieval readiness evaluation layer, and Stage 25 is the completed QA evaluator speed/diagnostics polish.

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
- Статус: completed.

## Stage 2. Проверить ETL на поддерживаемых форматах

- Цель: подтвердить, что текущий ETL baseline работает на поддерживаемых форматах, уже присутствующих в репозитории.
- Подзадачи:
  - подтвердить `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`;
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

- Цель: зафиксировать историческое baseline decision по `XLS` и таблицам без расширения scope за пределы текущего ETL/search baseline.
- Подзадачи:
  - подтвердить, что `XLSX` поддерживается на текущем baseline-уровне;
  - зафиксировать, что table blocks/chunks из `XLSX` попадают в retrieval path;
  - сохранить исторический контекст старого бинарного `XLS` как unsupported state на момент Stage 13;
  - не обещать полноценную table-aware reasoning / analytics.
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
- Историческая отметка:
  - Stage 14 superseded the Stage 13 unsupported-XLS state with practical `.xls` baseline support.

## Stage 14. XLS support and spreadsheet table hardening

- Цель: добавить минимальную практическую поддержку старого бинарного `.xls` и усилить baseline для spreadsheet/table input без перехода к полноценной table-aware analytics.
- Подзадачи:
  - выбрать минимальную open-source dependency strategy для `.xls`;
  - добавить `XlsExtractor` или эквивалентный extractor path для `.xls`;
  - привести `.xls` output к тому же baseline-контракту, что и `.xlsx`: heading/table raw blocks → `TableData` → `Block(type="table")` → chunks;
  - подтвердить обработку существующего sample `first_test_data/Форма 4 Затраты на сырье.XLS`;
  - зафиксировать поведение тестами на extractor, structure, saved JSON и search/ask path;
  - явно описать ограничения: formulas/macros/styles/merged cells/advanced Excel semantics не являются целью этапа.
- Рамка этапа:
  - не добавлять pandas/openpyxl/LibreOffice без отдельного обоснования;
  - не менять search ranking/API contract;
  - не делать полноценную table-aware reasoning;
  - не трогать OCR.
- Статус: completed.

## Stage 15. Customer demo readiness / ingestion-search QA alignment

- Цель: проверить и документировать, что можно честно показать заказчику после поддержки `xls`.
- Подзадачи:
  - провести read-only audit и docs/test alignment;
  - собрать supported format matrix;
  - собрать customer scenario support matrix;
  - проверить demo flow candidates: `batch_process`, `audit_corpus`, `rebuild_corpus`, `demo_search`, `ask` / `search` API;
  - сформировать next-stage recommendation.
- Рамка этапа:
  - не добавлять extraction features;
  - не добавлять OCR;
  - не добавлять summarization;
  - не добавлять generation;
  - не добавлять semantic/vector retrieval;
  - не добавлять table-aware analytics.
- Статус: completed.

## Stage 16. Summarization / draft generation spike

- Цель: после readiness stage проверить локальные или open-source варианты суммаризации и draft generation.
- Подзадачи:
  - сформировать небольшой proof-of-value scope;
  - не включать fine-tuning в roadmap как обещание;
  - рассматривать только локальные или open-source варианты, если они будут разрешены;
  - привязать выводы к качеству источников, ограничениям корпуса и source-backed evidence.
- Рамка этапа:
  - не заявлять полноценную генерацию проектной документации до фактической реализации и оценки качества;
  - не подменять source-backed extraction свободной генерацией без ссылок на источники.
- Статус: completed.

## Stage 17. Prototype integration flow

- Цель: собрать reproducible customer demo flow `process` / `audit` / `rebuild` / `search` / `ask` / table scenario после readiness и summarization steps, без обещаний новых AI-capabilities.
- Подзадачи:
  - связать подтверждённые части baseline и pilot track в один demo smoke runner;
  - оставить audit/eval visible в прототипе;
  - показать честный baseline: source-backed search, source-backed ask, table retrieval, audit visibility, image metadata-only limitation;
  - не заявлять полноценный RAG или end-to-end generation до фактической реализации;
  - подготовить основу для рабочего прототипа сервиса для экологов-проектировщиков.
- Статус: completed.

## Stage 17.1. Customer demo output polish

- Customer demo smoke runner output is localized to Russian and kept read-only by default.
- The demo report remains customer-facing and honest about current limitations.
- The table scenario probe is constrained to spreadsheet evidence and does not use non-spreadsheet files as proof of row-level table context.
- Stage 17.1 does not change API, search ranking, or retrieval semantics.

## Stage 18. Governance / roadmap audit

- Цель: сверить README, worklog, scenarios и finish-line notes с фактическим baseline после Stage 14–17.1.
- Подзадачи:
  - привести управляющие документы к одному актуальному описанию baseline;
  - убрать противоречия между историческими стадиями и текущим состоянием;
  - оставить понятный выбор следующих этапов без обещания уже не реализованных возможностей.
- Статус: completed.

## Stage 19.0. Delivery-first roadmap lock

- Цель: зафиксировать roadmap так, чтобы каждый следующий stage оставлял проект demo-ready / shippable и мог быть отброшен без поломки текущего baseline.
- Принцип stage-by-stage delivery:
  - каждый следующий stage имеет самостоятельную ценность;
  - future stages не должны быть обязательным условием для уже готового baseline;
  - не начинать большие архитектурные переписывания без отдельного решения;
  - все future AI capabilities идут через source-backed / evaluation-visible контур;
  - OCR / RAG / LLM generation не объявляются готовыми, пока это не подтверждено кодом.
- Cutline rule:
  - после Stage 19.0, 19.1, 19.2, 20 и далее должна быть понятная точка остановки и короткий путь к сдаче.
- Статус: completed.

## Stage 19.1. OCR candidate reporting / OCR-readiness without production OCR

- Цель: добавить read-only detection и reporting OCR candidates без запуска OCR и без изменения production intake.
- Подзадачи:
  - помечать standalone `jpg` / `jpeg` / `png` как OCR candidates в metadata-only режиме;
  - консервативно отмечать `pdf` без meaningful extracted text / chunks как possible scanned PDF / OCR candidate;
  - показывать OCR candidate summary в audit и customer demo runner;
  - честно фиксировать, что OCR baseline всё ещё не реализован.
- Артефакты:
  - `app/schemas/document.py`
  - `app/services/document_service.py`
  - `scripts/audit_corpus.py`
  - `scripts/demo_customer_flow.py`
  - `tests/test_extractors.py`
  - `tests/test_audit_corpus.py`
  - `tests/test_api.py`
- Статус: completed.

## Stage 20. Optional local OCR baseline for standalone JPG/PNG

- Цель: добавить минимальный optional local OCR baseline для standalone `jpg` / `jpeg` / `png` без внешних proprietary API и без обязательной новой тяжёлой зависимости.
- Подзадачи:
  - использовать локальный OCR adapter только для standalone image intake;
  - извлекать текст, если локальный engine доступен и вернул meaningful text;
  - сохранять OCR-text в обычный document output, чтобы он попадал в blocks/chunks/search/ask path;
  - оставлять metadata-only fallback и OCR-candidate reporting, если engine недоступен, упал или вернул пустой текст;
  - не затрагивать scanned PDF OCR и не менять unsupported image-like formats.
- Артефакты:
  - `app/pipeline/ocr.py`
  - `app/services/document_service.py`
  - `scripts/audit_corpus.py`
  - `scripts/demo_customer_flow.py`
  - `scripts/check_ocr.py`
  - `tests/test_extractors.py`
  - `tests/test_api.py`
  - `tests/test_audit_corpus.py`
  - `tests/test_demo_customer_flow.py`
- Статус: completed.

## Stage 21. OCR smoke evaluation / read-only quality check

- Цель: дать read-only smoke/eval проверку OCR readiness на image samples без записи в storage и без изменения production behavior.
- Подзадачи:
  - переиспользовать Stage 20 OCR adapter;
  - собрать per-file OCR summary для supported/unsupported image-like inputs;
  - не трогать scanned PDF OCR, RAG, LLM, vector DB, search ranking и batch ingestion behavior;
  - сохранять JSON-report только по явному флагу.
- Артефакты:
  - `scripts/evaluate_ocr.py`
  - `tests/test_evaluate_ocr.py`
- Статус: completed.

## Stage 22. Requirements extraction v1, source-backed, no generation

- Цель: добавить deterministic/rule-based extraction layer для возможных нормативных/обязательных требований из уже обработанных документов.
- Подтверждённый scope:
  - read-only чтение `storage/results`;
  - extractive candidates из исходного текста;
  - source fields: `document_id`, `filename`, `source_type`, block/chunk/table/section/page context where available;
  - category, score, matched terms и reason codes;
  - CLI `scripts.extract_requirements`;
  - минимальный read-only API endpoint `GET /api/v1/corpus/requirements`.
- Вне scope:
  - LLM generation, RAG, semantic retrieval, vector DB;
  - legal/compliance guarantee;
  - scanned PDF OCR и OCR strategy changes;
  - search ranking или `/ask` contract changes.
- Артефакты:
  - `app/extraction/requirements.py`
  - `scripts/extract_requirements.py`
  - `tests/test_requirements_extraction.py`
- Статус: completed.

## Stage 23. Table-aware evidence evaluation / calculation inputs v2

- Цель: добавить read-only deterministic evidence layer для таблиц и возможных входных данных экологических расчетов поверх уже обработанных `StructuredDocument` JSON.
- Подтверждённый scope:
  - чтение processed JSON / `StructuredDocument` без reprocess;
  - table evidence records с `document_id`, `filename`, table/block/chunk/section/page context where available;
  - conservative scoring по headers/cell text/domain terms;
  - категории `emissions`, `pollutants`, `limits_or_norms`, `measurements`, `costs_or_resources`, `sources_or_equipment`, `unknown`;
  - CLI `scripts.evaluate_tables`;
  - read-only API endpoint `GET /api/v1/corpus/tables`.
- Вне scope:
  - SQL-like table questions;
  - автоматические расчеты;
  - table analytics / table reasoning;
  - LLM/RAG/generation;
  - OCR strategy changes;
  - search ranking или `/ask` contract changes.
- Артефакты:
  - `app/extraction/tables.py`
  - `scripts/evaluate_tables.py`
  - `tests/test_table_evidence.py`
- Статус: completed.

## Stage 24. Golden QA / retrieval evaluation harness

- Цель: добавить read-only оценку готовности retrieval/QA по внешнему CSV dataset с вопросами, эталонными ответами и ожидаемыми документами-источниками.
- Подтверждённый scope:
  - CLI `scripts.evaluate_qa_dataset`;
  - CSV-first reader без новых dependencies;
  - чтение внешнего `Example_data/test_with_answers.csv` только по явному `--qa-path`;
  - чтение уже обработанных `StructuredDocument` JSON из `--results-dir`;
  - in-memory retrieval evaluation без записи в `storage/index`, `storage/results`, `storage/uploads`;
  - summary metrics для hit@1/@3/@5, source hit rate, answer/evidence token overlap, table-like question subset;
  - JSON report только по явному `--json-report-path`, рекомендуемый runtime каталог `.runtime_eval/`.
- Вне scope:
  - LLM/RAG generation;
  - embeddings/vector DB/semantic retrieval;
  - изменение production search ranking, `/ask` contract или ingestion pipeline;
  - scanned PDF OCR, OCR strategy changes;
  - SQL/table analytics;
  - коммит внешнего QA dataset или generated reports.
- Статус: completed.

## Stage 25. QA evaluator speed/diagnostics polish

- Цель: сделать `scripts.evaluate_qa_dataset` удобнее для регулярных smoke/eval прогонов без изменения production behavior.
- Подтверждённый scope:
  - evaluator остаётся read-only и читает внешний QA CSV только через явный `--qa-path`;
  - добавлены timing diagnostics в console output и JSON report: `load_qa_seconds`, `load_results_seconds`, `evaluate_seconds`, `write_report_seconds`, `total_seconds`, `avg_seconds_per_question`;
  - добавлен fast-флаг `--skip-answer-overlap`, который отключает extractive `ask`/answer-overlap слой и явно помечает `answer_overlap_evaluated=false`, не подменяя skipped результат нулевым score;
  - добавлен `--report-detail-level summary|failures|full`, где `full` остаётся default и наиболее совместим с Stage 24;
  - добавлены output limits `--failures-limit`, `--missing-source-limit`, `--top-hits-limit`, которые ограничивают размер report, но не меняют retrieval/top-k evaluation intent;
  - console output показывает mode, report detail level, skip answer overlap, total elapsed и avg seconds/question.
- Рекомендуемый регулярный smoke:
```powershell
conda run -n etl_env python -m scripts.evaluate_qa_dataset --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --skip-answer-overlap --report-detail-level summary --failures-limit 10 --missing-source-limit 5 --top-hits-limit 3 --json-report-path .runtime_eval\qa_smoke_summary.json
```
- Полный режим остаётся доступен по default или явно через `--report-detail-level full` без `--skip-answer-overlap`.
- Вне scope:
  - изменение production `/ask` contract;
  - изменение search ranking;
  - изменение ingestion pipeline;
  - OCR/scanned PDF OCR;
  - LLM, embeddings/vector DB, RAG generation;
  - коммит внешнего QA dataset или runtime reports.
- Статус: completed.

## Ближайший roadmap после QA evaluator

Следующие этапы идут последовательно и сохраняют delivery-first принцип: каждый stage должен оставлять проект demo-ready / shippable, без обязательной зависимости от будущих этапов.

## Stage 26. External QA dataset coverage audit

- Статус: completed.
- Цель: read-only аудит покрытия внешнего QA dataset до обработки внешних документов.
- Scope:
  - read-only анализ внешнего `Example_data`;
  - QA CSV coverage;
  - expected document references;
  - missing/no-source placeholders;
  - matching expected docs to files in `Example_data`;
  - duplicate/ambiguous matches;
  - supported/unsupported formats;
  - table-like/numeric question counts;
  - JSON report only to `.runtime_eval/` by explicit flag;
  - no ingestion, no production storage writes, no commit of external data.
- Артефакты:
  - `scripts.audit_external_qa_dataset`;
  - `tests/test_audit_external_qa_dataset.py`;
  - bounded JSON report по явному `--json-report-path`.
- Подготовка к Stage 27:
  - audit отделяет matched/missing/ambiguous expected documents;
  - Stage 27 должен использовать временный workspace и не писать в `storage/index`, `storage/results`, `storage/uploads`.
- Out of scope:
  - processing full external dataset;
  - changing search ranking;
  - changing `/ask`;
  - LLM/RAG/embeddings/vector DB;
  - OCR/scanned PDF OCR;
  - table analytics.

## Stage 27. External QA temporary workspace processing/eval

- Статус: completed.
- Цель: добавить safe temporary workspace workflow для внешнего QA dataset после Stage 26 audit.
- Scope:
  - CLI `scripts.evaluate_external_qa_workspace`;
  - default safe/dry-run behavior, если `--process` и `--run-eval` не указаны;
  - processing только по явному `--process`;
  - QA eval только по явному `--run-eval`;
  - `--source-scope expected|all-supported`, default `expected`;
  - `--ambiguous-policy skip|all`, default `skip`, без unsafe first-match fallback;
  - `--max-documents` для bounded smoke runs;
  - `--encoding` и `--delimiter` для явного чтения QA CSV/TSV, с UTF-8-safe default для обычных русских headers;
  - explicit `--workspace-report-path` используется как путь manifest/report и в processing/eval mode;
  - temporary workspace structure under `--workspace-dir`: `uploads/`, `results/`, `index/`, `reports/`, `workspace_manifest.json`;
  - QA evaluator запускается against `workspace/results`, не against production `storage/results`;
  - external dataset и `.runtime_eval/` не добавляются в repo.
- Подтверждённый safety contract:
  - production `storage/index`, `storage/results`, `storage/uploads` не должны загрязняться Stage 27 workflow;
  - ambiguous expected docs из Stage 26 по default не обрабатываются, а попадают в skipped examples;
  - `all-supported` и `ambiguous-policy all` требуют явных флагов и могут быть ограничены `--max-documents`.
- Out of scope:
  - external dataset commit/copy into repo;
  - production search ranking, `/api/v1/ask`, OCR strategy, scanned PDF OCR;
  - LLM/RAG generation, embeddings/vector DB, semantic retrieval;
  - aggressive fuzzy document selection.

## Stage 28. QA failure taxonomy / customer-readable diagnostics

- Статус: completed.
- Цель: классифицировать провалы QA/retrieval eval и сделать диагностику понятной для customer-facing анализа без обещания неподтверждённых AI capabilities.
- Scope:
  - read-only module `app.evaluation.qa_failure_taxonomy`;
  - CLI `scripts.diagnose_qa_failures`;
  - stable `taxonomy_version: "stage28_qa_failure_taxonomy_v1"`;
  - входной Stage 24/25 QA eval JSON обязателен;
  - Stage 26 external audit report и Stage 27 workspace manifest опциональны;
  - JSON diagnostics пишется только по явному `--output-path`;
  - console summary показывает количество вопросов, failures/limitations, counts by category и честные next actions;
  - классификация консервативна: если в старом report не хватает полей, item уходит в `unknown_or_needs_manual_review`.
- Out of scope:
  - production search/ranking changes;
  - `/api/v1/ask` contract changes;
  - ingestion pipeline changes;
  - OCR/scanned PDF OCR;
  - LLM/RAG/generation, embeddings/vector DB, semantic retrieval;
  - table analytics/calculations;
  - commit of external dataset or runtime reports/artifacts.

## Stage 29.0. Docs-only roadmap alignment after RAG chunk audit

- Статус: completed.
- Цель: зафиксировать outcome read-only RAG chunk audit без изменения production code, tests, storage или external dataset.
- Подтверждённый вывод:
  - текущие chunks acceptable for lexical search;
  - текущие chunks weak/partial as self-contained RAG handoff units;
  - ближайший приоритет - customer/developer-readable chunk inspection/export, а не speed/cache.
- Out of scope:
  - full RAG/LLM generation;
  - embeddings/vector DB;
  - OCR/reranking/table analytics;
  - production search/ranking changes.

## Stage 29.1. RAG-ready chunk inspection/export v1

- Статус: completed.
- Цель: дать customer/developer-readable inspection/export текущих chunks, чтобы видеть текст, source context и ограничения handoff units.
- Подтвержденный scope:
  - read-only CLI `scripts.export_rag_chunks`;
  - чтение существующих processed `StructuredDocument` JSON из `--results-dir`, default `storage/results`;
  - JSON report только по явному `--output-path`;
  - compact chunk export с document/source/section/page/table context where available;
  - conservative `content_type` и `quality_flags` без OCR/table analytics/LLM.
- Scope boundary: read-only diagnostics/export; без изменения ingestion, search ranking, `/api/v1/ask`, storage baseline или external dataset.

## Stage 29.2. Chunk quality audit v1

- Статус: completed.
- Цель: оценить chunk completeness/self-containedness/source-context gaps после inspection/export v1.
- Подтвержденный scope:
  - read-only модуль `app.evaluation.rag_chunk_quality`;
  - CLI `scripts.audit_rag_chunks` поверх existing processed JSON / Stage 29.1 export records;
  - JSON report только по явному `--output-path`, console summary без записи файла по default;
  - deterministic issue taxonomy для short/long/missing section/page/table-like/unknown/empty/low-context/duplicate/image-or-OCR-limited signals;
  - per-document aggregation, bounded samples, roadmap-linked recommendations для Stage 30/31/32.
- Scope boundary: deterministic audit/report only; без LLM/RAG generation, embeddings/vector DB, OCR, reranking или table analytics.

## Stage 30. RAG chunk contract hardening v1

- Статус: planned.
- Цель: уточнить контракт chunk payload/source context для будущего source-backed RAG handoff, не объявляя RAG готовым.
- Scope boundary: contract/docs/tests only where explicitly needed; без full RAG/LLM generation, semantic retrieval или vector DB.

## Stage 31. Table chunk context v1

- Статус: planned.
- Цель: улучшить читаемость table chunk context как handoff unit, сохранив lexical retrieval baseline.
- Scope boundary: context hardening only; без SQL/table analytics, automatic calculations или ranking rewrite.

## Stage 32. Source location/citation hardening

- Статус: planned.
- Цель: сделать source location/citation context более устойчивым для inspection, diagnostics и будущего source-backed handoff.
- Scope boundary: citation/source metadata hardening; без генерации ответов, external APIs или vector DB.

## Stage 33. QA evaluator retrieval-loop speed/cache

- Статус: optional / later.
- Условие запуска: только если после chunk inspection/export и quality audit скорость снова станет blocker.

## Final polish checkpoint

- Статус: deferred until explicit user command.
- Запускается только по явной команде пользователя: "стоп, следующий шаг делаем финал".

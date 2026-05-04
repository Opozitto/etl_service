# PLAN

Stage 1–32 are completed. Stage 1–6 are a closed baseline. Stage 7–9 are completed and form the local batch/evaluation foundation. Stage 10–17.1 are completed and documented below. Stage 18 is completed. Stage 19.0 is the delivery-first roadmap lock. Stage 20–25 are completed OCR/readiness/extraction/table/QA-evaluation layers. Stage 26–32 are completed external QA/chunk visibility, audit, chunk contract hardening, table chunk context, and source location/citation hardening stages. Stage 33 splitter structure cleanup and validation closure is completed from the splitter cleanup standpoint. Stage 34.0 text chunk coherence audit/design is completed docs-only. Stage 34.1 text chunk coherence edge cleanup v1 is completed as a bounded deterministic implementation. Stage 34.2 is completed docs-only as the finite finish roadmap lock after Stage 34.1 validation and metric reconciliation. The next stage is Stage 34.3 chunk quality taxonomy normalization/reporting v1; speed/cache remains distant backlog only.

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
- Граница scope:
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
- Вне scope:
  - processing full external dataset;
  - changing search ranking;
  - changing `/ask`;
  - LLM/RAG/embeddings/vector DB;
  - OCR/scanned PDF OCR;
  - table analytics.

## Stage 27. External QA temporary workspace processing/eval

- Статус: completed.
- Цель: добавить safe temporary workspace workflow для внешнего QA dataset после Stage 26 audit.
- Граница scope:
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
- Вне scope:
  - external dataset commit/copy into repo;
  - production search ranking, `/api/v1/ask`, OCR strategy, scanned PDF OCR;
  - LLM/RAG generation, embeddings/vector DB, semantic retrieval;
  - aggressive fuzzy document selection.

## Stage 28. QA failure taxonomy / customer-readable diagnostics

- Статус: completed.
- Цель: классифицировать провалы QA/retrieval eval и сделать диагностику понятной для customer-facing анализа без обещания неподтверждённых AI capabilities.
- Граница scope:
  - read-only module `app.evaluation.qa_failure_taxonomy`;
  - CLI `scripts.diagnose_qa_failures`;
  - stable `taxonomy_version: "stage28_qa_failure_taxonomy_v1"`;
  - входной Stage 24/25 QA eval JSON обязателен;
  - Stage 26 external audit report и Stage 27 workspace manifest опциональны;
  - JSON diagnostics пишется только по явному `--output-path`;
  - console summary показывает количество вопросов, failures/limitations, counts by category и честные next actions;
  - классификация консервативна: если в старом report не хватает полей, item уходит в `unknown_or_needs_manual_review`.
- Вне scope:
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
- Вне scope:
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
- Граница scope: read-only diagnostics/export; без изменения ingestion, search ranking, `/api/v1/ask`, storage baseline или external dataset.

## Stage 29.2. Chunk quality audit v1

- Статус: completed.
- Цель: оценить chunk completeness/self-containedness/source-context gaps после inspection/export v1.
- Подтвержденный scope:
  - read-only модуль `app.evaluation.rag_chunk_quality`;
  - CLI `scripts.audit_rag_chunks` поверх existing processed JSON / Stage 29.1 export records;
  - JSON report только по явному `--output-path`, console summary без записи файла по default;
  - deterministic issue taxonomy для short/long/missing section/page/table-like/unknown/empty/low-context/duplicate/image-or-OCR-limited signals;
  - per-document aggregation, bounded samples, roadmap-linked recommendations для Stage 30/31/32.
- Граница scope: deterministic audit/report only; без LLM/RAG generation, embeddings/vector DB, OCR, reranking или table analytics.

## Stage 30. RAG chunk contract hardening v1

- Статус: completed.
- Цель: уточнить и укрепить production contract для существующего `chunk` payload/source context, чтобы будущий source-backed RAG handoff мог опираться на более устойчивые handoff units, не объявляя RAG готовым.
- Подтвержденный scope:
  - `Chunk` получил backward-compatible optional поля для `content_type`, `source_type`, `section_title`, `section_path`, `page_start`, `page_end`, `source_filename`, `table_id`;
  - structure заполняет прямой section/page/content/table context там, где он уже детерминированно известен;
  - document service проставляет source visibility (`source_filename`, `source_type`) при новом processing;
  - Stage 29.1 export предпочитает новые прямые chunk fields, но сохраняет fallback для старых processed JSON;
  - Stage 29.2 audit принимает новые export/chunk-like records и сохраняет compatibility со старым shape.
- Граница scope: hardening существующего chunk/source contract; без full RAG/LLM generation, semantic retrieval, embeddings, vector DB, reranking, OCR или table analytics.

## Stage 31. Table chunk context v1

- Статус: completed.
- Цель: улучшить читаемость table chunk context как handoff unit, сохранив lexical retrieval baseline.
- Подтвержденный scope:
  - `Chunk` получил backward-compatible optional table-поля для readable handoff context: `table_title`, `table_headers`, `table_row_index`, `table_column_values`, `table_context`, `row_count`, `column_count`;
  - row-level table chunks получают детерминированный контекст таблицы/раздела/строки и header-to-value пары там, где headers уже доступны в extracted table rows;
  - chunks без headers сохраняют lexical row values без выдуманных header fields;
  - Stage 29.1 export показывает новые table-specific поля, но сохраняет fallback для старых processed JSON;
  - Stage 29.2 audit считает richer table context достаточным для table-like handoff diagnostics.
- Граница scope: context hardening only; без SQL/table analytics, automatic calculations, full RAG/LLM, embeddings/vector DB или ranking rewrite.

## Stage 32. Source location/citation hardening

- Статус: completed.
- Цель: сделать source location/citation context более устойчивым для inspection, diagnostics и будущего source-backed handoff.
- Подтвержденный scope:
  - `IndexedChunk` и backward-compatible API payload для `/api/v1/search` и `/api/v1/ask` теперь могут отдавать source/location hints: `source_filename`, `source_type`, `chunk_order`, `section_path`, `page_start`, `page_end`, `source_block_ids`, `table_id`, `table_row_index`, `location_label`, `citation_label`;
  - labels собираются детерминированно только из уже доступных filename/section/table/page fields и не выдумывают page, если page metadata отсутствует;
  - Stage 29.1 export добавляет `chunk_order`, `location_label`, `citation_label` и продолжает использовать fallback для старых processed JSON;
  - Stage 29.2 audit samples сохраняют source/location fields для диагностики проблемных chunks;
  - старые index/export/chunk-like records без новых полей остаются читаемыми.
- Граница scope: source/location/citation metadata hardening only; без full RAG, LLM citation generator, embeddings/vector DB, semantic retrieval, OCR/scanned PDF OCR, reranking или table analytics.

## Stage 33.0. Docs-only splitter roadmap realignment after manual chunk review

- Статус: completed.
- Цель: зафиксировать docs-only решение после ручного просмотра `rag_chunks_preview.json` по `test.docx`.
- Подтвержденный вывод:
  - Stage 30–32 strengthened metadata/source/location/citation contract for inspection, diagnostics and future source-backed handoff;
  - current chunks remain acceptable for lexical search;
  - clean customer/developer-readable handoff still depends on splitter structure cleanup;
  - speed/cache is no longer the closest recommended stage.
- Known splitter issues to address next:
  - TOC / оглавление не должно становиться родителем реальных content sections;
  - heading-only / short chunks нужно подавлять, объединять с соседним контекстом или явно маркировать как low-value;
  - duplicate heading text внутри chunks нужно дедуплицировать;
  - title-page / approval / signature blocks нужно лучше отделять от content/table chunks;
  - `section_path` должен отражать реальные разделы, а не структуру оглавления;
  - table-like classification должна быть осторожной;
  - DOCX page metadata can be unavailable; this limitation must stay explicit rather than invented.
- Граница scope: docs-only roadmap alignment; без production code, tests, storage, runtime reports или external dataset changes.

## Stage 33.1. Splitter structure cleanup v1

- Статус: completed.
- Цель: улучшить качество структуры `blocks` / `chunks` для более чистого customer/developer-readable handoff, сохранив delivery-first principle.
- Подтвержденный scope:
  - TOC / service headings (`СОДЕРЖАНИЕ`, `ОГЛАВЛЕНИЕ`, `TABLE OF CONTENTS`) больше не становятся parent hierarchy для последующих реальных body sections;
  - типовые standalone headings (`АННАТАЦИЯ` / `АННАТОЦИЯ` / `АННОТАЦИЯ`, `ВВЕДЕНИЕ`, `ЗАКЛЮЧЕНИЕ`) распознаются как headings без широкого fuzzy matching;
  - repeated heading prefix внутри chunk text дедуплицируется только при normalized-identical совпадении;
  - heading-only sections не эмитят самостоятельный обычный text chunk без полезного body text;
  - короткие approval/signature/service-like table blocks сохраняются как text blocks с metadata marker вместо meaningful `TableData` / `table_row` chunks;
  - реальные таблицы с row/header data сохраняют прежнюю row-level chunk логику;
  - export/audit/search автоматически получают cleaner `section_path`, fewer heading-only chunks и меньше false table row chunks для newly processed documents.
- Вне scope:
  - full RAG / LLM generation;
  - embeddings/vector DB / semantic retrieval / reranking;
  - OCR/scanned PDF OCR;
  - table analytics / SQL-like table QA / automatic calculations;
  - production search ranking rewrite.
- Known limitations:
  - cleanup conservative and deterministic, not semantic document understanding;
  - existing processed JSON remains readable but is not migrated;
  - DOCX page metadata can still be null and must not be invented;
  - title/signature/service detection is intentionally cautious and may not catch every layout artifact.

## Stage 33.2. Fresh splitter cleanup validation on temporary workspace

- Статус: completed.
- Цель: дать customer/developer-readable validation workflow, который заново обрабатывает выбранные sample documents в отдельном temporary workspace и оценивает качество Stage 33.1 cleanup на newly processed output, а не на старых `storage/results`.
- Подтвержденный scope:
  - CLI `scripts.validate_splitter_cleanup`;
  - reusable module `app.evaluation.splitter_cleanup_validation`;
  - fresh processing через `DocumentService(storage_root=...)` в explicit `--workspace-dir`;
  - input через repeatable `--input-path` или `--input-dir`, с optional `--max-documents`;
  - JSON report пишется только по явному `--output-path`; без него выводится console summary only;
  - deterministic metrics для TOC parent violations, duplicate heading text, heading-only chunks, service table suspects, real table chunk preservation и missing page expected limitations.
- Report contract:
  - `validation_version: "stage33_2_splitter_cleanup_validation_v1"`;
  - `summary`, `documents`, `issues`, `limitations`, `warnings`;
  - issue types: `toc_parent_violation`, `duplicate_heading`, `heading_only_chunk`, `service_table_suspect`, `processing_error`.
- Граница scope:
  - validation/evaluation only;
  - no migration of existing `storage/results`;
  - no full RAG, LLM generation, embeddings/vector DB, semantic retrieval, reranking, OCR/scanned PDF OCR, speed/cache work or table analytics.
- Known limitations:
  - validation is deterministic and conservative, not semantic document understanding;
  - existing processed JSON remains readable but is not migrated;
  - DOCX page metadata can still be null and is reported as an expected limitation, not invented;
  - service/title/signature detection is cautious and may require manual review for unusual layouts.

## Stage 33.3. Service table false-positive cleanup v2

- Статус: completed.
- Цель: точечно доработать deterministic cleanup для title/approval/signature table false positives после fresh validation Stage 33.2, сохранив реальные table chunks.
- Подтвержденный scope:
  - single-cell и compact approval/signature/title blocks с `"Утверждено"`, `Коммерческий директор`, `(подпись)`, slash placeholders, `2023 г.`, `(число)` / `(месяц)` демотируются из `table` в readable `paragraph` block с `table_classification: service_text`;
  - реальные таблицы с row/header context, spreadsheet `sheet_name`, содержательные DOCX/PDF tables и row-level chunks сохраняются;
  - validation detector согласован с cleanup: demoted service text не считается `service_table_suspect`, но old/unfixed table-like approval chunks остаются warning;
  - fresh validation remains evidence layer over newly processed temporary workspace outputs.
- Smoke evidence on `first_test_data\test.docx` in a fresh `.runtime_eval` workspace:
  - `documents_processed=1`;
  - `toc_parent_violations=0`;
  - `duplicate_heading_violations=0`;
  - `heading_only_chunks=0`;
  - `service_table_suspects=0`;
  - `real_table_chunks=950`;
  - `missing_page_expected_limitations=1426`.
- Граница scope:
  - no migration of existing `storage/results`;
  - no full RAG, LLM generation, embeddings/vector DB, semantic retrieval/reranking, OCR/scanned PDF OCR, speed/cache work or table analytics.
- Known limitations:
  - cleanup is deterministic and conservative, not semantic document understanding;
  - existing processed JSON can still contain old table false positives until documents are reprocessed;
  - DOCX page metadata can still be null and is not invented.

## Stage 33.4. Splitter cleanup validation closure docs

- Статус: completed.
- Цель: docs-only зафиксировать expanded fresh validation evidence после Stage 33.3 и закрыть Stage 33 со стороны splitter cleanup.
- Evidence run:
```powershell
conda run -n etl_env python -m scripts.validate_splitter_cleanup --input-dir first_test_data --workspace-dir .runtime_eval\splitter_stage33_4_workspace_dir --max-documents 4 --output-path .runtime_eval\splitter_stage33_4_report_dir.json
```
- Result:
  - `documents_seen=4`;
  - `documents_processed=4`;
  - `documents_with_failures=0`;
  - `total_chunks=1820`;
  - `toc_parent_violations=0`;
  - `duplicate_heading_violations=0`;
  - `heading_only_chunks=0`;
  - `service_table_suspects=0`;
  - `real_table_chunks=984`;
  - `missing_page_expected_limitations=1426`;
  - `issues_sample=[]`;
  - `warnings=[]`.
- Вывод:
  - Stage 33 can be considered closed from the splitter cleanup standpoint;
  - fresh splitter validation remains the evidence layer for newly processed temporary workspace outputs;
  - production `storage/results` is not migrated and remains outside this evidence source of truth.
- Remaining limitations:
  - existing processed JSON is not migrated;
  - DOCX page metadata may remain null and must not be invented;
  - deterministic cleanup is not semantic document understanding;
  - no OCR/scanned PDF OCR;
  - no full RAG / LLM generation;
  - no embeddings/vector DB / semantic retrieval / reranking;
  - no table analytics.
- Suggested next roadmap direction:
  - Stage 34.0 should audit ordinary text chunk coherence and prepare a bounded deterministic Stage 34.1 design;
  - speed/cache stays a later option only if it becomes a severe operational blocker.

## Stage 34.0. Text chunk coherence audit & implementation plan

- Статус: completed.
- Цель: docs-only audit/design для следующего этапа улучшения ordinary text chunks как source-backed handoff units после Stage 33 closure.
- Подтвержденный audit:
  - text chunks создаются в `app.pipeline.transform.structure._build_section_chunks`;
  - текущий код уже пакует text parts внутри section с `target_chars=850` и `max_chars=1200`, добавляет heading context один раз и сохраняет overlap после flush;
  - row-level table chunks создаются отдельно в `_build_table_row_chunks` и не должны смешиваться с text chunks;
  - `Chunk` contract уже содержит backward-compatible поля `content_type`, `source_type`, `section_title`, `section_path`, `page_start`, `page_end`, `source_filename`, `table_id` и table-specific поля Stage 31;
  - search/export/audit/API полагаются на `chunk_id`, `order`, `section_path`, `page_start/page_end`, `block_ids`/`source_block_ids`, `table_id`, `table_row_index`, `location_label`/`citation_label`.
- Fresh metrics on `.runtime_eval\stage34_0` over `test.docx`, `test.txt`, `Том 1 Инвентаризация Эко Агро.docx`, `Том 2 ПДВ Эко Агро.docx`:
  - splitter validation: `documents_processed=4`, `documents_with_failures=0`, `total_chunks=6061`, `toc_parent_violations=0`, `duplicate_heading_violations=0`, `heading_only_chunks=2`, `service_table_suspects=0`, `real_table_chunks=4008`;
  - RAG export: `content_type_counts={'table': 1106, 'table_row': 4008, 'text': 947}`;
  - text-only distribution: `text_chunks=947`, `short_text_chunks=29`, `nonservice_short_text_chunks=25`, `avg_text_chars=823.22`, `median_text_chars=884`, `min_text_chars=6`, `max_text_chars=1160`, `single_paragraph_text_chunks=2`, `one_line_text_chunks=2`, `avg_text_source_blocks=7.67`;
  - table chunks dominate this fresh sample: `5114/6061`, about `84.38%`.
- Stage 34.1 recommended design:
  - keep deterministic text packing inside one section only;
  - never cross section boundary and never merge table chunks with text chunks;
  - preserve heading context once, ordered union of source `block_ids`, `section_path`, page range where block metadata has pages, source filename/type, content type, and all table fields compatibility;
  - bound chunk size around internal target `700–1200` chars without adding CLI/API complexity by default;
  - suppress or attach low-value heading/title fragments only when deterministic and safe;
  - keep old processed JSON readable and avoid API schema breaking changes.
- Risks:
  - lexical search scores and snippets may change because chunk granularity changes;
  - longer chunks may be less exact as snippets;
  - tests assuming exact chunk counts or first hit ordering may need targeted updates;
  - table row chunks and rich table context must not regress;
  - `source_block_ids` must stay ordered and trustworthy;
  - old processed JSON remains old until reprocessed.
- Acceptance criteria for Stage 34.1:
  - full local `conda run -n etl_env python -m pytest -q` green, or Codex sandbox limitation explicitly separated from project failures;
  - fresh splitter validation still has zero TOC parent, duplicate heading and service table failures on bounded sample;
  - short non-service text chunks decrease, or at minimum no new bad short examples appear;
  - meaningful section text chunks include coherent neighboring context without crossing sections;
  - table chunk count/context is not radically degraded;
  - export/audit/search/API tests stay green;
  - demo customer flow still passes.
- Вне scope:
  - no full RAG / LLM generation;
  - no embeddings/vector DB / semantic retrieval / reranking;
  - no OCR/scanned PDF OCR;
  - no speed/cache work;
  - no table analytics / SQL-like QA;
  - no production storage/results migration.

## Stage 34.1. Text chunk coherence / chunk packing v1

- Статус: completed.
- Цель: точечно улучшить coherence ordinary text chunks после Stage 34.0 audit, сохранив splitter/search/export/API compatibility.
- Реализация:
  - final `flush` больше не эмитит standalone overlap-only chunk без нового текста;
  - короткий fresh final tail внутри той же section merge-ится в предыдущий ordinary text chunk, если итог остаётся в пределах существующего `max_chars`;
  - ordered `block_ids`, page range и token estimate обновляются при merge;
  - structural heading-only fragments и короткие uppercase root-title fragments без body context не эмитятся как ordinary text chunks;
  - table row-level path `_build_table_row_chunks` не менялся.
- Fresh validation on `.runtime_eval\stage34_1_final` over the Stage 34.0 explicit 4-file sample:
  - `documents_processed=4`;
  - `documents_with_failures=0`;
  - `total_chunks=6029`;
  - `toc_parent_violations=0`;
  - `duplicate_heading_violations=0`;
  - `heading_only_chunks=0`;
  - `service_table_suspects=0`;
  - `real_table_chunks=4008`.
- Fresh text metrics:
  - `text_chunks=921`;
  - `table_chunks=5108`;
  - `short_text_chunks=25`;
  - `nonservice_short_text_chunks=21`;
  - `avg_text_chars=837.34`;
  - `median_text_chars=887`;
  - `min_text_chars=20`;
  - `max_text_chars=1167`;
  - `single_paragraph_text_chunks=0`;
  - `one_line_text_chunks=0`.
- Граница scope: deterministic chunk packing only; no full RAG, LLM generation, embeddings/vector DB, semantic retrieval/reranking, OCR/scanned PDF OCR, speed/cache work, table analytics, or production storage migration.

## Stage 34.2. Finite finish roadmap lock after chunk coherence

- Статус: completed / docs-only.
- Цель: зафиксировать конечную последовательность после Stage 34.1 и audit-only metric reconciliation, чтобы не уйти в бесконечную splitter/chunk polishing петлю.
- Подтверждено после Stage 34.1:
  - post-commit exact validation на explicit 4-file sample прошла без failures;
  - `documents_processed=4`;
  - `documents_with_failures=0`;
  - `total_chunks=6029`;
  - `toc_parent_violations=0`;
  - `duplicate_heading_violations=0`;
  - `heading_only_chunks=0`;
  - `service_table_suspects=0`;
  - `real_table_chunks=4008`.
- Audit-only reconciliation показал, что apparent growth of short chunks связан с разной taxonomy, а не с прямой регрессией Stage 34.1:
  - raw `content_type` counts: `total=6029`, `text=921`, `table=1100`, `table_row=4008`, `table + table_row=5108`;
  - broad collector относил к table chunks с `table_id`, `table_row_index` или `table_column_values`, даже если `content_type='text'`;
  - mixed text chunks with `table_id=234`;
  - `raw text 921 - 234 = collector text 687`;
  - `raw table-ish 5108 + 234 = collector table 5342`;
  - `real_table_chunks=4008` означает strict stable `table_row` chunks, а не все table-linked chunks;
  - short threshold discrepancy: raw `content_type='text'` `<250` gives `57` short / `52` nonservice, while `<120` gives `25` short / `21` nonservice.
- Remaining compact chunks в inspected exact sample в основном не подтверждены как bad tails:
  - title/cover fragments;
  - TOC/list fragments;
  - formula/calculation micro-sections;
  - pollutant/equipment micro-evidence;
  - confirmed real problematic low-value tails: `0`.
- Вывод:
  - Stage 34.1 считается валидным;
  - Stage 34.2 ничего не меняет в production behavior;
  - Stage 34.3, а не Stage 34.2, является следующим implementation/reporting stage;
  - cleanup v2 запрещён по умолчанию и допускается только после Stage 35 evidence of repeated real problems.
- Вне scope для финального маршрута:
  - full RAG;
  - LLM generation;
  - embeddings/vector DB;
  - semantic retrieval/reranking;
  - scanned PDF OCR;
  - embedded DOCX/PDF OCR;
  - speed/cache work;
  - table analytics / SQL-like QA;
  - production UI;
  - external proprietary API.

## Stage 34.3. Chunk quality taxonomy normalization/reporting v1

- Статус: planned next.
- Цель: унифицировать chunk metrics/reporting taxonomy после Stage 34.1/34.2, чтобы raw `content_type`, broad table-linked counts, `real_table_chunks`, short thresholds и service/nonservice categories не сравнивались как одно и то же.
- Ожидаемый scope:
  - reporting/audit taxonomy only;
  - clearly separate raw `content_type` counts from table-linked broad collector counts;
  - show `<120` and `<250` short thresholds explicitly;
  - keep formula/evidence micro-chunks separate from true low-value tails;
  - no splitter behavior change unless a later evidence stage requires it.

## Stage 35. External Example_data validation v1

- Статус: planned.
- Цель: проверить текущий ETL/source-backed handoff baseline на external `D:\Projects\etl_service_backup\Example_data` как evidence run, без training, без commit external dataset и без production storage migration.
- Ожидаемый scope:
  - explicit temporary workspace only;
  - report validation and chunk taxonomy evidence;
  - compare repeated real issues against first_test_data evidence;
  - keep ambiguous/missing source handling conservative.

## Stage 36. Targeted cleanup v2, only if needed

- Статус: conditional planned.
- Условие запуска: только если Stage 35 покажет repeated real problems, not just metric taxonomy noise or acceptable compact evidence chunks.
- Возможные targets:
  - title/cover fragments;
  - TOC/list fragments after title pages;
  - conservative formula micro-chunk handling only if repeatedly harmful;
  - other true low-value tails confirmed by external evidence.
- Запрещено:
  - broad splitter rewrite;
  - semantic document understanding claims;
  - cleanup for one-off cosmetic fragments without repeated evidence.

## Stage 37. Optional light OCR handoff polish, only if time remains

- Статус: optional / droppable.
- Условие запуска: только если Stage 34.3/35/36 are completed or explicitly dropped and time remains.
- Цель: лёгкая handoff/readiness polish вокруг уже существующей OCR candidate / standalone image OCR visibility.
- Вне scope:
  - scanned PDF OCR;
  - embedded DOCX/PDF OCR;
  - layout/table OCR;
  - production OCR expansion.

## Final delivery preparation

- Статус: planned after Stage 34.3/35 and any explicitly needed conditional stages.
- Цель: подготовить честный delivery package around confirmed ETL/search/ask/evaluation/chunk handoff baseline.
- Правила:
  - no endless splitter polishing;
  - no cleanup v2 unless Stage 35 evidence shows repeated real issue;
  - no final polish until explicit command or after planned stages are done/dropped;
  - keep limitations honest and avoid claiming full RAG, LLM, vector search, scanned PDF OCR or table analytics.

## Stage 33.x. QA evaluator retrieval-loop speed/cache

- Статус: distant backlog / optional.
- Условие запуска: только если скорость станет severe operational blocker after splitter structure cleanup and evidence diagnostics.
- Не является ближайшим recommended stage.

## Final polish checkpoint

- Статус: deferred until explicit user command.
- Запускается только по явной команде пользователя: "стоп, следующий шаг делаем финал".

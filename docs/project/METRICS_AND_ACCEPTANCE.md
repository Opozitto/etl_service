# METRICS AND ACCEPTANCE

## Назначение

Этот документ закрывает пункт ТЗ: "Используемая метрика оценки качества и сравнения моделей - должна быть определена исполнителем".

В текущем проекте нет обученной LLM/генеративной модели и нет full RAG. Поэтому метрика не описывается как accuracy модели генерации. Проект решает ETL-задачу первого этапа: разделение документов на `blocks` / `chunks`, извлечение текста и таблиц, подготовка `StructuredDocument` JSON и локального search/source-backed QA handoff. Качество такого baseline измеряется набором воспроизводимых quality gates по слоям пайплайна.

Иными словами, "метрика" в рамках текущей поставки - это не одно число, а согласованный набор acceptance metrics, которые исполнитель определяет для ETL/RAG-readiness: обработка документов, качество структуры/chunks, контекст таблиц, retrieval/source-backed QA readiness, OCR smoke для standalone images и operational acceptance.

## Metric groups

### 1. Document processing metrics

Цель группы - показать, что документы проходят ingest/processing предсказуемо, а ошибки и ограничения видны.

- `documents_seen` - сколько входных файлов найдено workflow.
- `documents_selected` - сколько файлов выбрано для обработки после фильтров, source matching и scope rules.
- `documents_processed` - сколько файлов успешно обработано в `StructuredDocument` JSON.
- `documents_failed` - сколько файлов завершились ошибкой обработки.
- `processing_success_rate` - доля успешно обработанных документов среди выбранных.
- Unsupported format counts - количество файлов по неподдерживаемым расширениям/типам.
- Ambiguous/missing expected source diagnostics for external QA - диагностика, когда expected source из QA-файла не найден однозначно или отсутствует.
- Runtime storage pollution check - подтверждение, что smoke/eval временные прогоны не оставили tracked files в `storage/index`, `storage/results`, `storage/uploads`; эти каталоги являются local generated output и должны быть absent or ignored.

Acceptance смысл: успешность обработки должна быть измеримой, а zero-document или ambiguous-source runs не должны выдаваться за успешную оценку качества корпуса.

### 2. Structure / chunk quality metrics

Цель группы - проверить, что output пригоден для поиска, ручного аудита и будущего source-backed handoff.

- `total_chunks` - общее количество chunk records.
- `raw_content_type_counts` - raw counts по `content_type`.
- `text`, `table`, `table_row`, `image` counts - базовая видимость типов контента.
- `heading_only_chunks` - chunks, состоящие только из заголовка без полезного body context.
- `duplicate_heading_violations` - повтор заголовков в chunk text после deterministic cleanup.
- `toc_parent_violations` - случаи, когда TOC/оглавление стало родителем реальных body sections.
- `service_table_suspects` - подозрения на service/title/signature blocks, ошибочно выглядящие как meaningful tables.
- `severe_short_text <120` - очень короткие text chunks, отдельно от обычных compact evidence fragments.
- `compact_text_evidence <250` - компактные text chunks, которые требуют taxonomy interpretation, но не являются автоматическим дефектом.

Compact taxonomy buckets:

- `title_or_cover_fragment`;
- `toc_or_list_fragment`;
- `formula_or_calculation_micro_evidence`;
- `pollutant_or_equipment_micro_evidence`;
- `real_low_value_tail`;
- `service_or_boilerplate`;
- `other_compact_text`.

Acceptance смысл: не все короткие chunks плохие. Формулы, pollutant/equipment snippets и табличные micro-evidence могут быть полезны для retrieval/source-backed review. Cleanup justified только при повторяемых `real_low_value_tail` или других подтвержденных real problems.

### 3. Table context metrics

Цель группы - проверить readable context для row-level table chunks без заявления table analytics.

- `strict_table_row_chunks` - chunks с raw `content_type='table_row'`.
- `strict_table_row_chunks_with_column_values` - strict table rows, где доступны `table_column_values`.
- `strict_table_row_chunks_with_rich_row_context` - strict table rows с readable row/table context.
- `chunks_with_table_id` - chunks с привязкой к `table_id`.
- `chunks_with_table_row_index` - chunks с row index.
- `chunks_with_table_column_values` - chunks с header-to-value / column values.
- `mixed_text_with_table_context` - text chunks, которые несут table context и должны считаться отдельно от обычного текста.

Эта группа не является table analytics, SQL-like QA или automatic calculations. Она проверяет, что табличные строки и связанные fragments читаемы, трассируемы и пригодны для source-backed retrieval/review.

### 4. Retrieval / QA readiness metrics

Цель группы - оценить, насколько текущий lexical search / extractive QA path находит ожидаемые source-backed evidence.

- `hit@1` - ожидаемый источник найден первым результатом.
- `hit@3` - ожидаемый источник найден в top 3.
- `hit@5` - ожидаемый источник найден в top 5.
- `source_hit_rate` - доля вопросов, где найден ожидаемый source.
- `evidence_overlap_avg` - средний overlap найденного evidence с ожидаемыми source/evidence terms.
- `answer_overlap_avg` - средний overlap answer text с expected answer, только когда используется full/default evaluator mode.

`--skip-answer-overlap` - это fast smoke mode для более быстрого retrieval/source smoke. Он не заменяет полную оценку, если нужно сравнивать answer-overlap trend или readiness для extractive QA.

Acceptance смысл: измеряется retrieval/source-backed readiness, а не качество LLM generation. Система должна уметь показать источник или честно вернуть отсутствие информации в корпусе.

### 5. OCR baseline metrics

Цель группы - smoke/eval видимость для существующего optional local OCR baseline.

- Scope: только standalone `jpg`, `jpeg`, `png`.
- OCR engine availability - найден ли локальный OCR engine.
- Available languages - какие language packs доступны.
- Selected OCR language - выбранная конфигурация, например `rus+eng`.
- Success/failure counts - сколько image samples обработано успешно или с ошибкой/fallback.
- Extracted text length / preview sanity - длина извлеченного текста и bounded preview для sanity review.

CER/WER пока не считаются, потому что в baseline нет ground truth для OCR. Если в будущем появится размеченная выборка, CER/WER можно добавить как отдельную metric group.

Scanned PDF OCR и embedded image OCR inside DOCX/PDF не реализованы. OCR baseline не использует external/proprietary OCR API и не является production OCR quality guarantee.

### 6. Operational acceptance gates

Цель группы - финально подтвердить delivery-ready состояние без расширения scope.

- Full pytest в локальном `etl_env`.
- Focused pytest where applicable для конкретно затронутых модулей.
- `demo_customer_flow` smoke.
- API smoke для core endpoints.
- OCR smoke для standalone images.
- External validation smoke по explicit external dataset path, без commit external files/reports.
- Single-file inspector smoke через `scripts.inspect_document_structure`: один явно указанный файл, isolated workspace под `.runtime_eval` или explicit safe path, bounded console/Markdown/JSON report, production `storage` не изменяется.
- `git diff --check`.
- UTF-8/BOM/U+FFFD sanity для Markdown/docs.
- Runtime storage clean: `git ls-files storage/index storage/results storage/uploads` пустой, `git check-ignore -v` подтверждает ignore для storage probes, а локальные `storage/index`, `storage/results`, `storage/uploads` после demo/eval отсутствуют или остаются ignored generated output.

Acceptance смысл: delivery проверяется воспроизводимыми командами и чистотой артефактов, а не устными claims.

Эксплуатационные команды, recommended demo route, temporary workspace policy и cleanup порядок описаны в `docs/project/OPERATION_GUIDE.md`. Метрики воспроизводятся через scripts/evaluation workflows, упакованные в `experiments/README.md`.

Финальный acceptance checklist, cleanup перед физической копией и правила copy/commit зафиксированы в `docs/project/FINAL_DELIVERY_CHECKLIST.md`.

## Comparison of approaches

Сравнивать в текущем проекте нужно не модели генерации, а версии ETL pipeline / extractor / splitter / chunker / OCR configuration по одним и тем же quality gates.

Примеры корректных сравнений:

- before/after splitter cleanup: `heading_only_chunks`, `duplicate_heading_violations`, `toc_parent_violations`, `service_table_suspects`, `severe_short_text <120`, `compact_text_evidence <250`.
- default OCR vs `--language rus+eng`: OCR engine/language availability, success/failure counts, extracted text length, preview sanity.
- strict expected-source mode vs exploratory all-supported mode: `documents_selected`, `documents_processed`, ambiguous/missing source diagnostics, chunk quality counts.
- full QA eval vs fast smoke mode: `hit@k`, `source_hit_rate`, `evidence_overlap_avg`, and `answer_overlap_avg` only in full/default mode.

Это не обещает model training, LLM generation, embeddings/vector DB, semantic retrieval, scanned PDF OCR, embedded image OCR, table analytics или production UI.

## Minimal acceptance criteria for final delivery

Финальная поставка считается минимально приемлемой, если:

- supported formats documented: `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`, плюс standalone `jpg`/`jpeg`/`png` для optional local OCR baseline.
- ETL produces `StructuredDocument` JSON with sections, blocks, chunks, tables/images metadata where available.
- API starts and core endpoints are tested.
- Search/ask source-backed behavior works and no-answer case remains explicit.
- Table rows have readable row/table/column context where deterministic metadata is available.
- Audit/eval scripts are documented and distinguish diagnostics from production behavior.
- Single-file structure inspector is available for manual handoff review of one arbitrary file without production storage pollution.
- OCR limitations are honest: standalone image OCR является optional/local; scanned PDF OCR и embedded image OCR не реализованы.
- Для подтверждённого baseline не требуются external proprietary API.
- External dataset используется только by path и не коммитится.
- Runtime artifacts не коммитятся, включая `.runtime_eval` reports/workspaces и generated `storage/index`, `storage/results`, `storage/uploads` from local processing/smoke/eval runs.
- Known limitations and next steps are explicit.

## Explicit non-claims

Текущий acceptance baseline не заявляет готовыми:

- full RAG;
- LLM generation / answer synthesis;
- semantic retrieval / reranking;
- embeddings/vector DB;
- scanned PDF OCR;
- embedded image OCR inside DOCX/PDF;
- SQL/table analytics или automatic calculations;
- production UI;
- external proprietary APIs.

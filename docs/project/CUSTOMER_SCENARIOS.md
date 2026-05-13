# CUSTOMER SCENARIOS

## Назначение документа

Документ был создан на Stage 10 как docs-level baseline для пользовательских сценариев и минимального evaluation set. Сейчас он актуализируется по мере развития ETL/search/evaluation baseline и отражает текущее состояние после Stage 39.0 post-audit triage lock.

Сценарии описывают пилотный контур для эколога-проектировщика: source-backed search, extractive QA, extraction/evidence diagnostics, контроль качества корпуса и подготовку chunk handoff для будущего source-backed RAG layer. Документ не объявляет готовыми full RAG, LLM generation, embeddings/vector DB, semantic retrieval, scanned PDF OCR или table analytics.

Метрики и acceptance gates для проверки этих сценариев зафиксированы в `docs/project/METRICS_AND_ACCEPTANCE.md`.

## Основной пользователь

Основной пользователь: эколог-проектировщик.

Он работает с исходными файлами клиента, нормативными документами, проектной документацией, шаблонами и методическими материалами. Для него важны source-backed поиск, extractive QA, извлечение требований, поиск входных данных для расчетов, контроль качества корпуса и прозрачность источников.

## MVP / pilot scenarios

Все сценарии ниже остаются source-backed. Они могут использовать существующий корпус, audit visibility и chunk diagnostics, но не обещают generated answers или ungrounded synthesis.

### S1. Source-backed search

Пользователь ищет фрагменты или разделы в документах клиента или нормативных материалах.

Ожидаемый результат:

- список найденных documents / chunks;
- `file` / `filename` / `document_id`;
- `section_title`;
- `snippet`;
- `score` / `rank`.

### S2. Source-backed extractive QA

Пользователь задает вопрос по загруженным документам.

Ожидаемый результат:

- короткий ответ, строго основанный на найденных источниках;
- ссылки на `file` / `document_id` / `chunk` / `section`;
- если данных нет, явное `нет информации в корпусе`.

### S3. Requirements extraction

Пользователь просит найти требования или нормативные условия.

Ожидаемый результат:

- найденные требования как extractive snippets;
- ссылки на источники;
- candidate category / score / matched terms where available;
- без генерации новых требований и без legal/compliance guarantee.

### S4. Calculation inputs discovery

Пользователь ищет данные для расчетов или обоснований.

Ожидаемый результат:

- найденные числовые и текстовые фрагменты;
- ссылки на источники;
- candidate tables с headers, preview rows, category/tags, score и matched terms where available;
- честная отметка, если нужны таблицы, OCR или ручная проверка.

### S5. Document quality / audit

Пользователь или разработчик проверяет, пригоден ли корпус для работы.

Ожидаемый результат:

- batch report;
- corpus audit;
- retrieval eval;
- problem documents;
- явные limitations вместо обещания неподтвержденных AI capabilities.

### S6. OCR / image intake candidate

Пользователь загружает скан или фотографию документа.

Текущий результат:

- metadata-only fallback, если локальный OCR engine недоступен;
- OCR candidate detection / reporting;
- optional local OCR baseline для standalone `jpg` / `jpeg` / `png`, если engine доступен;
- language-aware OCR smoke/eval для standalone images через local Tesseract, включая рекомендуемый `--language rus+eng` для русских документов;
- OCR без RU language config не считается quality baseline, потому что может дать misleading латинизированный или искаженный русский текст;
- OCR без RU language config допустим только как smoke/best-effort behavior;
- scanned PDF OCR не обещается как готовый.

Post-audit scope freeze:

- scanned PDF OCR остается вне подтвержденного baseline;
- embedded image OCR inside DOCX/PDF остается вне подтвержденного baseline;
- table/table-layout OCR и full document layout analysis остаются вне текущего scope.
- Stage 39.1 ограничен safety gate для standalone OCR и docs wording;
- scanned PDF OCR, embedded DOCX/PDF OCR, advanced OCR pipeline и OCR overhaul не planned.

### S7. Summarization / draft generation candidate

Пользователь просит summary или draft section.

Ожидаемый результат на текущем этапе:

- future spike only;
- не обещать summarization или LLM generation как готовые возможности.

### S8. Chunk inspection / RAG-ready handoff diagnostics

Пользователь или разработчик проверяет, как документ разбит на chunks и насколько chunks пригодны для будущего source-backed RAG layer.

Ожидаемый результат:

- chunk text / preview;
- `filename`;
- `document_id`;
- section path where available;
- page where available;
- `content_type`;
- `quality_flags`;
- strengthened source/location/citation fields after Stage 30–32 where available;
- limitations / handoff notes.

Это diagnostics/handoff visibility после Stage 29.1/29.2, metadata/source contract hardening после Stage 30–32 и splitter cleanup после Stage 33.1/33.3. Это не full RAG, не semantic retrieval, не embeddings/vector DB и не generation.

Текущий splitter cleanup v1:

- TOC / оглавление больше не должно становиться parent для real body sections в newly processed documents;
- repeated heading text дедуплицируется только при safe normalized-identical совпадении;
- heading-only chunks подавляются, если нет полезного body text;
- короткие approval/signature/service-like table blocks осторожно демотируются в text blocks, чтобы не выглядеть meaningful table chunks;
- реальные table row chunks сохраняются.

Stage 33.3 cleanup v2:

- compact и single-cell title/approval/signature table false positives с `"Утверждено"`, `Коммерческий директор`, `(подпись)`, slash placeholders, `2023 г.`, `(число)` / `(месяц)` демотируются в readable `service_text`;
- реквизитные и содержательные DOCX/PDF tables, spreadsheet rows и реальные row-level table chunks сохраняются;
- existing processed JSON не мигрируется, новое поведение применяется к newly processed documents.

Stage 33.2 validation:

- заново обрабатывает выбранные sample documents в explicit temporary workspace;
- проверяет newly processed JSON, а не старые production `storage/results`;
- показывает TOC parent violations, duplicate heading text, heading-only chunks, service table suspects, real table chunk preservation и expected missing page limitations;
- остается deterministic ETL validation, не RAG/LLM/embeddings/vector DB/reranking/OCR/table analytics.
- после Stage 33.3 используется как evidence layer для проверки service table false-positive cleanup v2 на fresh processing.
- Stage 33.4 closure evidence: expanded fresh validation on 4 `first_test_data` documents passed with `documents_processed=4`, `documents_with_failures=0`, `service_table_suspects=0`, `real_table_chunks=984`, `issues_sample=[]` and `warnings=[]`.

Stage 34.0 text chunk coherence audit/design:

- зафиксировал, что ordinary text chunks уже пакуются section-local deterministic логикой, но короткие title/appendix fragments всё ещё встречаются;
- fresh metrics на 4 explicit sample files: `text_chunks=947`, `table_chunks=5114`, `short_text_chunks=29`, `median_text_chars=884`;
- next recommended Stage 34.1 должен улучшать только deterministic text chunk coherence / chunk packing v1 без full RAG, LLM generation, embeddings/vector DB, semantic retrieval/reranking, OCR/scanned PDF OCR, speed/cache или table analytics.

Stage 34.1 text chunk coherence edge cleanup:

- overlap-only final buffers больше не становятся standalone chunks;
- короткие final tails внутри той же section могут merge-иться в предыдущий ordinary text chunk с сохранением ordered source blocks и page range;
- structural heading-only и короткие uppercase root-title fragments без body context не эмитятся как ordinary text chunks;
- fresh metrics на том же 4-file sample: `text_chunks=921`, `table_chunks=5108`, `nonservice_short_text_chunks=21`, `heading_only_chunks=0`, `real_table_chunks=4008`.

Stage 34.2 finite finish roadmap lock:

- post-commit exact validation после Stage 34.1 подтвердила `documents_processed=4`, `documents_with_failures=0`, `total_chunks=6029`, `toc_parent_violations=0`, `duplicate_heading_violations=0`, `heading_only_chunks=0`, `service_table_suspects=0`, `real_table_chunks=4008`;
- audit-only reconciliation объяснил, что apparent growth of short chunks связан с разной taxonomy: raw `content_type` counts were `text=921`, `table=1100`, `table_row=4008`, while broad collector moved `234` text chunks with table links into table counts;
- short threshold mismatch also matters: raw text `<250` gives `57` short / `52` nonservice, while raw text `<120` gives `25` short / `21` nonservice;
- remaining compact chunks are categorized as title/cover fragments, TOC/list fragments, formula/calculation micro-sections, and pollutant/equipment micro-evidence; confirmed real problematic low-value tails were `0` in the inspected exact sample;
- next customer-facing handoff improvement is unified chunk quality taxonomy/reporting, not more splitter polishing by default.

Stage 34.3 chunk quality taxonomy/reporting:

- audit report now separates raw `content_type` counts from broad table-linked counts and strict `content_type='table_row'` evidence;
- `content_type='text'` with `table_id`, `table_row_index` or `table_column_values` is reported as mixed text-with-table context, not ordinary text;
- short metrics are normalized into `severe_short_text <120` and `compact_text_evidence <250`, each split into `total`, `service`, and `nonservice`;
- compact `<250` chunks are classified into deterministic evidence buckets, including formula/calculation micro-evidence and pollutant/equipment micro-evidence, and are not automatic defects;
- recommendations stay conservative: no cleanup is needed unless `real_low_value_tail` or another real problem repeats;
- splitter/chunk-building logic did not change, so Stage 34.1 remains valid and the discrepancy is treated as taxonomy/reporting issue, not splitter regression.

Planned external evidence:

- Stage 35 validates against external `Example_data` in an explicit temporary workspace;
- `Example_data` is external evidence only, not training data, not copied into the repository and not committed;
- `scripts.validate_external_example_data` produces machine-readable reports under `.runtime_eval` by default:
  - `.runtime_eval\stage35_external_dataset_audit.json`;
  - `.runtime_eval\stage35_external_workspace_eval.json`;
  - `.runtime_eval\stage35_external_qa_eval.json`;
  - `.runtime_eval\stage35_external_chunk_quality.json`;
  - `.runtime_eval\stage35_external_validation_summary.json`;
- external validation applies Stage 34.3 taxonomy to workspace processed JSON and keeps compact `<250` chunks as evidence taxonomy, not automatic defects;
- strict expected-source mode can select/process zero documents when external expected sources are ambiguous; Stage 35 reports this as workflow attention with `chunk_quality_status=skipped_no_processed_documents`, not as successful chunk quality evidence and not as splitter regression;
- for exploratory non-empty ETL/chunk validation, run bounded `--source-scope all-supported` and/or `--ambiguous-policy all` with `--max-documents`;
- cleanup v2 is allowed only if non-empty external validation shows repeated real chunk problems.

Stage 36 targeted external chunk tail inspection:

- broad splitter cleanup is not justified yet: Stage 35 exploratory evidence showed only small candidate volume (`real_low_value_tail=3`, `severe_short_text=5`, `compact_text_evidence=6`);
- compact taxonomy sample export is available as opt-in report evidence, not as a behavior change;
- `scripts.audit_rag_chunks` supports `--include-samples`, `--sample-limit` and `--sample-buckets`;
- `scripts.validate_external_example_data` supports `--chunk-quality-include-samples`, `--chunk-quality-sample-limit` and `--chunk-quality-sample-buckets`;
- expected sample evidence is under `compact_text_taxonomy.samples.<bucket>[]` and includes document/source/chunk/section/page/block/table context, bounded `preview`, `char_length`, `reason_codes`, `matched_terms`, `quality_flags` and `handoff_notes`;
- local external inspection completed: chunk quality status was `ok` over `9` processed documents and `2145` chunks, while workflow/dataset/workspace status still remained `needs_attention` due to external dataset/workflow classification;
- only `3` `real_low_value_tail` candidates appeared out of `2145` chunks, all from one document, `4 Площадка №1 Выгрузка (пшеница)`;
- these samples look like isolated table/layout-derived text fragments, not a repeated cross-document structural defect;
- `pollutant_or_equipment_micro_evidence` samples are acceptable compact evidence with source/equipment/emission terms, not cleanup targets;
- final Stage 36 cleanup decision: splitter cleanup was not performed and is not needed now; future cleanup only if repeated tails appear across more documents/corpora.

Stage 39.0 post-audit triage lock:

- цель Stage 39 не "улучшить всё", а убрать misleading success-looking behavior перед delivery;
- bounded remediation: F1 standalone OCR misleading RU output, F2 RTF garbage extraction, F3 PDF `(cid:...)` garbage fragments;
- accepted limitation / preflight wording: F4 `.doc` converter/dependency issue;
- accepted deterministic ETL limitations, not remediation targets: missing DOCX pages, formula-like heading fragments, compact pollutant/equipment evidence, isolated table-layout tails, approval/signature service structures, partial multirow header limitations;
- finite route: Stage 39.1 standalone OCR safety gate, Stage 39.2 extractor garbage detection, Stage 39.3 final post-audit verification & docs alignment, then final delivery preparation only;
- not planned: scanned PDF OCR, embedded DOCX/PDF OCR, semantic retrieval, reranking, vector DB, full RAG, advanced OCR pipeline, large splitter rewrites, endless cleanup/polish.

### S9. Single-file structure inspection / handoff

Пользователь или разработчик хочет проверить один произвольный документ до добавления его в regular corpus flow.

Текущий результат после Stage 38.2:

- CLI `scripts.inspect_document_structure` принимает explicit path к одному файлу;
- обработка идет только во временный workspace, default `.runtime_eval\inspect_document_structure_workspace`;
- console summary печатается по умолчанию, Markdown/JSON отчеты пишутся только по explicit output path;
- отчет показывает metadata, processing info, sections, blocks, chunks, tables, images, warnings и workspace artifacts для ручного просмотра;
- production `storage/index`, `storage/results` и `storage/uploads` не загрязняются.

Это customer/developer-readable inspection/handoff tool для проверки разбиения произвольного документа. Это не UI, не RAG, не semantic retrieval, не embeddings/vector DB и не generation.

## Вне текущего подтвержденного baseline

Сейчас вне подтвержденного baseline:

- scanned PDF OCR;
- embedded DOCX/PDF image OCR;
- advanced OCR pipeline;
- semantic retrieval;
- reranking;
- embeddings/vector DB;
- full RAG;
- LLM generation / answer synthesis;
- summarization / draft generation как готовая функция;
- automatic generation of documentation fragments;
- HEIC как готовый intake path;
- XLS/XLSX table intelligence beyond the current baseline;
- SQL/table analytics или automatic calculations;
- production UI;
- external proprietary APIs.
- large splitter rewrites;
- endless cleanup/polish.

## Ожидаемые результаты документа

Этот документ фиксирует не новую функциональную реализацию, а pilot track contract:

- пользовательские сценарии;
- expected outputs для search, QA, extraction, audit и chunk diagnostics;
- ограничения текущего baseline;
- minimal evaluation set;
- связь с будущими stage.

## Acceptance criteria

- Сценарии сформулированы для эколога-проектировщика, а не для абстрактного пользователя.
- У каждого MVP / pilot сценария есть ожидаемый результат, связанный с source-backed behavior.
- Сценарии проверяются через metrics/acceptance baseline из `docs/project/METRICS_AND_ACCEPTANCE.md`.
- OCR / RAG / LLM generation не объявляются готовыми, если это не подтверждено кодом.
- Minimal evaluation set покрывает границы supported now / diagnostics / future.
- Материал связывает исторический Stage 10 baseline с текущим состоянием после Stage 39.0.

## Minimal evaluation set

Минимальный набор evaluation cases фиксирует, какие задачи должны проходить через текущий baseline, а какие должны честно оставаться ограниченными.

| id | scenario | user_question_or_task | input_scope | expected_behavior | expected_sources_required | current_stage_support | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EC-01 | Source-backed search | Найти `экология проект` в корпусе | Local corpus index and saved JSON results | Вернуть top hits с `file`, `document_id`, `section_title`, `snippet`, `score` / `rank` | yes | supported now | Basic retrieval proof |
| EC-02 | Requirements search | Найти требования для ПДВ / emissions | Documents from client corpus and normative source files | Показать extractive snippets со ссылками на источники | yes | supported now | Requirements must be extracted, not generated |
| EC-03 | Extractive QA | Какой срок или условие указаны в документе? | Chunk-level corpus content | Короткий ответ строго по источникам | yes | supported now | Если ответа нет, вернуть `нет информации в корпусе` |
| EC-04 | No-answer case | Есть ли информация про X, если ее нет? | Relevant corpus subset | Явно сказать, что информация отсутствует | yes | supported now | Проверяет честный отказ без hallucination |
| EC-05 | Calculation inputs | Найти исходные данные для расчета | Text and numeric fragments in docs | Вернуть numbers/fragments и candidate table previews со ссылками | yes | supported now / diagnostics | Stage 23 adds read-only table evidence evaluation; no automatic calculations |
| EC-06 | Audit visibility | Документ без chunks должен быть отмечен audit | Batch corpus outputs and audit report | Попасть в problem documents / audit summary | no | supported now | Linked to the Stage 7-9 reporting layer |
| EC-07 | OCR limitation / candidate visibility | Скан или фото документа | JPG / JPEG / PNG / HEIC candidate inputs | Отметить metadata-only fallback, OCR candidates, optional local OCR baseline для standalone images and language-aware smoke/eval when engine/language packs are available | no | Stage 20 / 37 diagnostics | Do not promise scanned PDF OCR or embedded DOCX/PDF image OCR; for Russian smoke use `--language rus+eng`; HEIC/HEIF/TIFF/TIF/BMP/WEBP stay unsupported |
| EC-08 | Table input | XLS / XLSX table-heavy document | Spreadsheet or table-like source | XLS and XLSX supported at baseline level with flattened lexical retrieval plus read-only table evidence candidates | yes | supported now / diagnostics | Row-level chunks and Stage 23 evidence improve source-backed preview; still not table-aware analytics |
| EC-09 | Summarization | Сделать краткое summary документа | Source document plus request for summary | Future spike only | yes | future | Do not announce ready summarization |
| EC-10 | Draft generation | Подготовить draft section документации | Project doc context and task brief | Future spike only | yes | future | Do not announce ready LLM generation |
| EC-11 | Source attribution | Показать, откуда взят ответ | Search hits and chunk references | Ответ должен содержать explicit source references | yes | supported now | Trust criterion for the pilot track |
| EC-12 | Problem documents | Найти проблемные документы в корпусе | Index, manifest, batch and audit reports | Audit surfaces duplicates, warnings, missing chunks and low-quality items | no | supported now | Uses the Stage 7-9 reporting layer |
| EC-13 | RAG-ready chunk export/audit | Проверить качество chunks как handoff units | Existing processed JSON / Stage 29.1 chunk export records | Показать chunk text/preview, `filename`, `document_id`, section path, page where available, raw `content_type`, table-linked context, strict table-row evidence, compact chunk taxonomy, `quality_flags`, strengthened source/location/citation fields where available, limitations and recommendations | yes | supported now / diagnostics | Stage 29.1/29.2 plus Stage 30–34.3 metadata/source/splitter/taxonomy hardening; no embeddings/vector DB/generation |
| EC-14 | Fresh splitter cleanup validation | Проверить Stage 33 cleanup на свежей обработке sample documents | Explicit input files/directories plus temporary workspace | Reprocess samples into workspace, then report TOC parent violations, duplicate headings, heading-only chunks, service table suspects, real table chunks and missing page limitations | yes | supported now / diagnostics | Stage 33.2 validates newly processed output; Stage 33.4 records 4-document closure evidence; no migration of production `storage/results` |
| EC-15 | External Example_data validation | Проверить handoff baseline на внешнем customer-like dataset | External `D:\Projects\etl_service_backup\Example_data` plus QA TSV file by explicit path | Audit QA coverage/source matching, process selected docs into temporary workspace, run QA/readiness eval, workflow summary and Stage 34.3 chunk taxonomy report | yes | supported now / diagnostics | Stage 35 workflow; strict expected-source mode may select 0 docs if sources are ambiguous, so exploratory chunk validation can use bounded `all-supported` / `ambiguous-policy all`; external files and `.runtime_eval` reports are not committed |
| EC-16 | External compact tail inspection | Проверить конкретные compact taxonomy chunks перед cleanup decision | External Stage 35 workspace or explicit temporary results dir | Export bounded `compact_text_taxonomy.samples.real_low_value_tail` with source/chunk/context metadata and preview | yes | supported now / diagnostics | Stage 36 inspection/reporting completed; current local evidence does not justify splitter cleanup |
| EC-17 | Single-file structure inspection | Проверить разбиение одного произвольного документа перед handoff/review | Explicit single file path plus temporary workspace | Обработать файл вне production storage и показать metadata, sections, blocks, chunks, tables, images, warnings и artifacts для ручного просмотра | yes | supported now / diagnostics | Stage 38.2 `scripts.inspect_document_structure`; not UI, not RAG, not semantic retrieval, not generation |
| EC-18 | Standalone OCR safety | Проверить русский standalone image OCR | Standalone JPG/JPEG/PNG with Russian text | Использовать `--language rus+eng` для quality baseline; без RU language config не считать output quality evidence | no | bounded remediation | Stage 39.1 target; no scanned PDF OCR, no embedded image OCR, no OCR overhaul |
| EC-19 | Extractor garbage classification | Проверить RTF/PDF output на мусор | RTF with garbage output / PDF with `(cid:...)` fragments | Отразить suspicious extraction как warning/degraded evidence вместо clean success | yes | bounded remediation | Stage 39.2 target; no parser replacement and no OCR fallback |

## Связь со Stage 11-17

- Stage 11 proves ask / extractive QA with sources поверх текущего корпуса, не превращая это в generation.
- Stage 12 tests OCR / image intake and separates confirmed support from limitations, especially for scans and phone photos.
- Stage 13 keeps the historical XLS / tables decision; Stage 14 superseded the old unsupported-XLS state with practical baseline support.
- Stage 15 aligns customer demo readiness, ingestion-search QA, supported formats and the scenario matrix after XLS support.
- Stage 16 treats summarization / draft generation as a future spike, not a baseline claim.
- Stage 17 connects confirmed parts into a prototype integration flow while keeping audit and eval visible.
- Stage 19.1 adds OCR candidate reporting and read-only visibility, while Stage 20 adds optional local OCR baseline for standalone images only.
- Stage 21 adds a separate read-only OCR smoke evaluation script for image readiness checks.
- Stage 22/23 add source-backed requirements and table evidence diagnostics without generation or table analytics.
- Stage 24/25 add QA/retrieval readiness evaluation and evaluator diagnostics without changing production retrieval behavior.
- Stage 29.1/29.2 add chunk inspection/export and quality audit for future handoff diagnostics.
- Stage 30–32 strengthen chunk metadata/source/table/location/citation fields without claiming full RAG.
- Stage 33.1 improves splitter structure for newly processed documents without changing retrieval into semantic/vector/LLM behavior.
- Stage 33.2 validates splitter cleanup on freshly processed temporary workspace outputs without migrating production storage.
- Stage 33.3 reduces title/approval/signature table false positives for newly processed documents while preserving real table chunks.
- Stage 33.4 closes splitter cleanup validation from the current roadmap standpoint using expanded fresh validation evidence.
- Stage 34.0 audits text chunk coherence and prepares Stage 34.1 as a bounded deterministic packing stage without changing production behavior.
- Stage 34.1 implements bounded deterministic text chunk coherence edge cleanup without changing table row-level chunks, API schema, or production storage migration.
- Stage 34.2 locks the finite finish route after chunk coherence and metric reconciliation.
- Stage 34.3 implements the customer-facing handoff improvement: unified chunk quality taxonomy/reporting.
- Stage 35 validates external `Example_data` as evidence only; it is not training and not committed.
- Stage 36 adds targeted compact taxonomy sample export for cleanup decision evidence and closes the current decision as cleanup not needed now.
- Stage 37 adds language-aware OCR smoke/eval and handoff polish for standalone image OCR without claiming production OCR.
- Stage 39.0 locks post-audit triage: bounded remediation is limited to misleading OCR/extractor garbage behavior, accepted deterministic ETL limitations stay explicit, and the route ends at Stage 39.3 plus final delivery preparation.

## Текущее состояние после Stage 39.0 post-audit triage

- Stage 29.1 adds read-only RAG-ready chunk inspection/export over existing processed JSON.
- Stage 29.2 adds read-only chunk quality audit over existing processed JSON / exported chunk records.
- Stage 30 hardens chunk/source contract for future source-backed handoff.
- Stage 31 strengthens table chunk context.
- Stage 32 strengthens source location/citation context.
- Stage 33.1 strengthens splitter structure cleanup v1 for newly processed documents.
- Stage 33.2 adds fresh splitter cleanup validation on explicit temporary workspace outputs.
- Stage 33.3 strengthens deterministic service/title/approval/signature table false-positive cleanup.
- Stage 33.4 records expanded fresh validation over 4 `first_test_data` documents with zero failures/warnings and closes Stage 33 from the splitter cleanup standpoint.
- Stage 34.0 records audit/design for text chunk coherence and recommends Stage 34.1 Text chunk coherence / chunk packing v1.
- Stage 34.1 reduces short/heading-only text chunk edge cases while preserving table row-level context and compatibility paths.
- Stage 34.2 records exact post-commit validation and reconciles raw `content_type`, broad table-linked collector counts and short threshold differences.
- Stage 34.2 confirms Stage 34.1 is valid and not a direct short-chunk regression.
- Stage 34.3 turns that reconciliation into explicit audit JSON/console reporting for raw `content_type`, broad table-linked counts, strict `table_row` evidence, short thresholds and compact chunk taxonomy.
- Stage 34.3 confirms compact `<250` chunks are evidence taxonomy, not automatic defects, and does not change splitter/chunk-building logic.
- Stage 35 adds a reproducible external validation workflow over `Example_data` with JSON reports for dataset audit, temporary workspace eval, QA/readiness eval and chunk quality taxonomy.
- Stage 35 workflow summary distinguishes zero-document ambiguous-source runs from real chunk quality evidence and recommends bounded exploratory reruns before cleanup decisions.
- Stage 35 keeps external files and runtime reports out of commits and does not change splitter/chunk-building logic, retrieval ranking, OCR, API, RAG/LLM/vector behavior or table analytics.
- Stage 36 adds bounded compact taxonomy sample export for `real_low_value_tail` and other selected buckets through audit CLI and external validation wrapper.
- Stage 36 local external inspection found `3` `real_low_value_tail` candidates out of `2145` chunks, all from one document and consistent with isolated table/layout-derived fragments.
- Stage 36 does not perform splitter cleanup and closes the current cleanup decision as not needed now.
- Stage 37 completed optional light OCR handoff polish: `check_ocr` lists available Tesseract languages when possible, `evaluate_ocr` supports `--language`, and Russian OCR smoke/eval should use `--language rus+eng` when language packs are installed.
- Stage 39.0 completed docs-only audit triage after deep audit of real `first_test_data`.
- Stage 39.0 explicitly separates bounded remediation from accepted limitations and prevents reopening the roadmap.
- Stage 39.1–39.3 are the only post-audit remediation route before final delivery preparation.
- Chunks now have better visibility, stronger metadata/source/location/citation context, and cleaner deterministic section/chunk structure where available.
- Splitter cleanup is conservative and improves handoff quality, but it is not semantic document understanding.
- Text chunk coherence remains bounded and deterministic: ordinary text chunks should not cross sections, merge with tables, invent pages, or change API schema in a breaking way.
- Unified chunk quality taxonomy/reporting is now available and separates real problems from metric/taxonomy noise.
- DOCX page metadata can still be unavailable; diagnostics should show this honestly rather than inventing page context.
- These stages should not promise full RAG, semantic retrieval, embeddings/vector DB, LLM generation, scanned PDF OCR or table analytics.
- These stages should also not promise embedded DOCX/PDF OCR, reranking, vector DB, advanced OCR pipeline, large splitter rewrites or endless cleanup/polish.
- Speed/cache is not the default next step, and there is no endless splitter polishing by default.

## Notes on the current baseline

- Stage 7-9 already provide batch reporting, corpus audit and retrieval quality evaluation.
- The confirmed direction remains source-backed search, source-backed proof, deterministic extraction/evidence and transparent diagnostics.
- OCR candidate reporting is the current read-only bridge for image limitations; standalone image OCR baseline is optional / local only.
- Spreadsheet/table support remains flattened lexical retrieval plus deterministic table evidence, not full table reasoning.

## Stage 14 note

- EC-08 reflects practical `.xls` / `.xlsx` support at baseline level.
- The scenario set still uses flattened lexical retrieval and deterministic table evidence, and does not claim full table reasoning.
- Row-level spreadsheet chunks and Stage 23 table evidence improve source-backed table row/value discovery without SQL/table analytics or automatic calculations.

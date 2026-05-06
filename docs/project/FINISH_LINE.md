# FINISH_LINE

## Delivery-first finish strategy

- The roadmap now stays delivery-first: every next stage should leave the project demo-ready / shippable on its own.
- Future stages may be dropped without breaking the current baseline.
- Any future AI capability should remain source-backed and evaluation-visible.
- Large architecture rewrites stay out of scope unless there is a separate decision.

## Current baseline

- ETL baseline runs end-to-end in the confirmed local environment.
- Supported document formats: `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`.
- Standalone `jpg` / `jpeg` / `png` now have an optional local OCR baseline: when a local engine is available, extracted text is written into the normal document output; otherwise they remain OCR candidates in metadata-only mode.
- PDFs without meaningful extracted text / chunks can still be conservatively surfaced as possible scanned PDF / OCR candidates, but scanned PDF OCR itself is not implemented.
- `HEIC` / `HEIF` / `TIFF` / `TIF` / `BMP` / `WEBP` remain unsupported image-like formats.
- `XLS` and `XLSX` are extracted into JSON, flow into chunks/search/ask, and use flattened lexical retrieval.
- Row-level chunks for tables add `sheet` / `table` / `row` / `column-value` context, but this is still lexical retrieval, not table-aware analytics.
- Table evidence evaluation is available as a read-only readiness layer for finding table candidates, headers, preview rows, and likely calculation input categories; it is not SQL/table analytics and does not perform automatic calculations.
- Customer demo smoke runner is available as a read-only CLI helper and honestly shows the current baseline limitations.
- Requirements extraction v1 is available as a deterministic source-backed candidate layer over processed JSON; it extracts snippets with source context and does not provide a legal/compliance guarantee.
- RAG-ready chunk inspection/export is available as a read-only visibility layer over existing processed JSON; it exposes chunk text/preview, document/source context, conservative `content_type`, `quality_flags`, and limitations for future handoff review.
- Chunk quality audit is available as a read-only diagnostic layer for chunk completeness/self-containedness/source-context gaps; it reports deterministic issues and recommendations, but does not make the system a RAG implementation.
- Chunk contract hardening v1 is completed: newly processed chunks can carry direct optional source/section/page/content/table context for future source-backed handoff while old processed JSON remains readable.
- Table chunk context v1 is completed: newly processed row-level table chunks can carry deterministic table title/context, headers, row index, header-to-value pairs, and table shape where available; this improves source-backed handoff readability but is not table analytics.
- Source location/citation hardening is completed: search/ask/export/audit can surface deterministic source/location hints such as filename, source type, chunk order, section path, page range, block ids, table id/row index, and location/citation labels where existing metadata supports them.
- Stage 33.1 splitter cleanup v1 is completed: newly processed documents get cleaner TOC hierarchy, repeated-heading deduplication, heading-only suppression, and cautious service/title/signature table handling.
- Stage 33.2 fresh splitter cleanup validation is completed: selected sample documents can be reprocessed into an explicit temporary workspace and evaluated with a deterministic report over newly processed JSON, not old production results.
- Stage 33.3 service table false-positive cleanup v2 is completed: compact and single-cell title/approval/signature blocks are demoted to readable `service_text` paragraphs, while real table chunks remain preserved.
- Stage 33.4 splitter cleanup validation closure is completed: expanded fresh validation on 4 `first_test_data` documents passed with zero failures, zero warnings and zero service table suspects.
- Stage 34.0 text chunk coherence audit/design is completed: no code behavior changed, and the next recommended implementation is bounded deterministic Stage 34.1 text chunk coherence / chunk packing v1.
- Stage 34.1 text chunk coherence edge cleanup v1 is completed: short final tails, overlap-only final buffers and low-value heading/title fragments are handled more conservatively without changing table row chunks or API schema.
- Stage 34.2 finite finish roadmap lock is completed docs-only: post-Stage 34.1 exact validation and metric reconciliation are recorded, and the remaining route is finite rather than open-ended splitter polishing.
- Stage 34.3 chunk quality taxonomy normalization/reporting v1 is completed: audit reports now separate raw `content_type`, broad table-linked context, strict `table_row` evidence, `<120` severe short text, `<250` compact evidence taxonomy, and cleanup recommendations.
- Stage 35 External `Example_data` validation v1 is completed: external dataset audit, temporary workspace processing/eval, QA readiness eval, workflow summary and Stage 34.3 chunk taxonomy can be run reproducibly through `scripts.validate_external_example_data` with JSON reports under `.runtime_eval`.
- Stage 36 targeted external chunk tail inspection / cleanup decision v1 is completed: compact taxonomy samples can be exported through `scripts.audit_rag_chunks` or the Stage 35 wrapper, local external evidence was inspected, and splitter cleanup is not justified now.
- Stage 37 optional OCR handoff polish is completed: OCR smoke/eval can pass an explicit Tesseract language config, JSON/console reports include `ocr_language`, and `check_ocr` surfaces installed Tesseract languages when available.
- Stage 38.1 metrics and acceptance documentation is recorded in `docs/project/METRICS_AND_ACCEPTANCE.md`: final acceptance relies on reproducible ETL/RAG-readiness quality gates rather than a single generative model accuracy metric.
- Stage 38.2 single-file structure inspector is available through `scripts.inspect_document_structure`: one explicit file is processed into an isolated `.runtime_eval` workspace by default, and console/Markdown/JSON reports show metadata, sections, blocks, chunks, tables, images, warnings and artifacts for handoff review.
- Stage 38.3 operation manuals are recorded in `docs/project/OPERATION_GUIDE.md`: quick start, explained operating route and detailed final handoff instructions for the confirmed ETL/source-backed baseline.
- Stage 30–34.3 strengthened the metadata/source/structure/validation/governance contract, but this is still ETL/source-backed handoff readiness rather than full RAG.

## Best shippable baseline

- supported formats: `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`.
- source-backed search/ask with explicit evidence.
- spreadsheet table retrieval with row-level lexical context.
- read-only table evidence evaluation for possible calculation inputs.
- audit/demo runner for corpus visibility and customer flow.
- optional local OCR baseline for standalone images when a local engine is available.
- OCR candidate reporting for image-only intake and conservative PDF readiness visibility.
- deterministic requirements candidate extraction with source context.
- read-only RAG-ready chunk inspection/export for visibility and handoff diagnostics.
- read-only chunk quality audit for handoff-readiness diagnostics.
- backward-compatible chunk/source context hardening for future source-backed handoff.
- readable table chunk context for future source-backed handoff without SQL-like QA or calculations.
- source location/citation hints for future handoff traceability without LLM citation generation.
- splitter structure cleanup for cleaner section paths and fewer low-value heading/service chunks in newly processed documents.
- fresh splitter cleanup validation for temporary workspace outputs without migrating production `storage/results`.
- single-file structure inspector for customer/developer-readable inspection of one arbitrary file without production storage pollution.
- Stage 33 closure evidence: 4-document fresh validation over `first_test_data` passed with `documents_with_failures=0`, `service_table_suspects=0`, and `real_table_chunks=984`.
- Stage 34.0 evidence: fresh temporary audit over 4 explicit sample files found `text_chunks=947`, `table_chunks=5114`, `short_text_chunks=29`, `median_text_chars=884`, and table-heavy outputs dominating the sample; this is design evidence, not a behavior change.
- Stage 34.1 evidence: on the same explicit 4-file fresh sample, `heading_only_chunks=0`, `nonservice_short_text_chunks=21`, `single_paragraph_text_chunks=0`, `one_line_text_chunks=0`, and `real_table_chunks=4008`.
- Stage 34.2 evidence: post-commit exact validation after Stage 34.1 had `documents_processed=4`, `documents_with_failures=0`, `total_chunks=6029`, `toc_parent_violations=0`, `duplicate_heading_violations=0`, `heading_only_chunks=0`, `service_table_suspects=0`, `real_table_chunks=4008`.
- Stage 34.2 metric reconciliation: raw `content_type` counts were `text=921`, `table=1100`, `table_row=4008`; a broad collector counted `234` text chunks with table links as table chunks, producing collector `text=687` and `table=5342`.
- Stage 34.2 short-chunk reconciliation: raw text `<250` gives `57` short / `52` nonservice, while raw text `<120` gives `25` short / `21` nonservice; the apparent growth is taxonomy/threshold mismatch, not a direct Stage 34.1 regression.
- Stage 34.3 reporting makes that reconciliation explicit in JSON/console output: compact `<250` chunks are classified as evidence taxonomy and are not automatic defects; cleanup is reserved for repeated `real_low_value_tail` or other confirmed repeated problems.
- Stage 35 evidence workflow:
```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --process --run-eval --run-chunk-quality --clean-workspace
```
- Stage 35 expected JSON reports: `.runtime_eval\stage35_external_dataset_audit.json`, `.runtime_eval\stage35_external_workspace_eval.json`, `.runtime_eval\stage35_external_qa_eval.json`, `.runtime_eval\stage35_external_chunk_quality.json`, `.runtime_eval\stage35_external_validation_summary.json`.
- Stage 35 strict expected-source mode can currently produce `selected=0 processed=0 skipped_ambiguous=7` on real `Example_data` because expected sources are ambiguous; this is dataset/workflow attention, not splitter regression.
- If `--run-chunk-quality` is requested with zero processed documents, Stage 35 reports `chunk_quality_status=skipped_no_processed_documents` and `status=needs_attention` instead of treating the empty audit as successful cleanup evidence.
- For exploratory non-empty ETL/chunk validation, use bounded runs with `--source-scope all-supported` and/or `--ambiguous-policy all` plus `--max-documents`.
- Stage 35 does not commit external dataset files, `.runtime_eval` reports or workspace artifacts; it also does not clean up chunks.
- Stage 36 inspection command for `real_low_value_tail` samples:
```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --source-scope all-supported --ambiguous-policy all --process --run-chunk-quality --clean-workspace --max-documents 10 --chunk-quality-include-samples --chunk-quality-sample-limit 5 --chunk-quality-sample-buckets real_low_value_tail --chunk-quality-report-path .runtime_eval\stage36_external_chunk_quality_samples.json --workflow-report-path .runtime_eval\stage36_external_validation_summary.json
```
- Stage 36 expected sample fields live under `compact_text_taxonomy.samples.<bucket>[]`; they include document/source/chunk/section/page/block/table context, bounded `preview`, `char_length`, `reason_codes`, `matched_terms`, `quality_flags` and `handoff_notes`.
- Stage 36 local external evidence:
  - workflow/dataset/workspace status still `needs_attention`, with `qa_eval_status=None`; this is external dataset/workflow classification and not a claim that QA/dataset status is fully OK;
  - chunk quality status `ok` over `documents_processed=9` and `total_chunks=2145`;
  - raw content types: `text=399`, `table=228`, `table_row=1518`, `image=0`;
  - table path remains separate and strong: `chunks_with_table_id=1969`, `chunks_with_table_row_index=1518`, `chunks_with_table_column_values=1503`, `mixed_text_with_table_context=223`;
  - strict table evidence: `strict_table_row_chunks=1518`, `strict_table_row_chunks_with_column_values=1503`, `strict_table_row_chunks_with_rich_row_context=1518`;
  - compact taxonomy: `pollutant_or_equipment_micro_evidence=3`, `real_low_value_tail=3`, all other compact buckets `0`.
- Stage 36 sample interpretation:
  - the `3` `real_low_value_tail` candidates are only `3/2145` chunks and all came from one document, `4 Площадка №1 Выгрузка (пшеница)`;
  - samples `chk-3`, `chk-7`, `chk-8` look like isolated table/layout-derived text fragments, not a repeated cross-document structural defect;
  - `pollutant_or_equipment_micro_evidence` samples are acceptable compact evidence, not cleanup targets.
- Stage 36 cleanup decision: splitter cleanup was not performed and is not needed now. Future cleanup should only be considered if repeated tails appear across more documents/corpora.
- Stage 37 OCR smoke commands:
```powershell
conda run -n etl_env python -m scripts.check_ocr
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir <dir> --json-report-path <path> --language rus+eng
```
- Stage 37 remains smoke/eval and handoff polish only. OCR quality depends on image quality, installed language packs, preprocessing and future OCR module design. Future OCR provenance should preserve source path/name, page, artifact/image id, engine/version, language config, confidence if available, processing timestamp and source modality; OCR-derived chunks should be marked explicitly as OCR-derived evidence.

## Final delivery toolkit

- `docs/project/METRICS_AND_ACCEPTANCE.md` - quality gates and acceptance baseline.
- `docs/project/OPERATION_GUIDE.md` - operation manual for quick start, explained demo route, detailed handoff, temporary workspace policy and cleanup.
- `scripts.demo_customer_flow` - customer-facing baseline smoke.
- `scripts.inspect_document_structure` - single-file structure inspection without production storage pollution.
- `scripts.audit_rag_chunks` - chunk quality / handoff diagnostics.
- `scripts.validate_external_example_data` - external `Example_data` path-only validation workflow.
- `scripts.check_ocr` and `scripts.evaluate_ocr` - optional local standalone image OCR smoke/eval.

## What is confirmed, and what is not

- Confirmed:
  - source-backed search;
  - source-backed ask / extractive QA;
  - corpus audit visibility;
  - corpus rebuild;
  - spreadsheet table retrieval with row-level context;
  - read-only OCR candidate reporting;
  - optional local OCR baseline for standalone images when a local engine is available.
  - read-only OCR smoke evaluation script for image readiness checks.
  - deterministic source-backed requirements candidate extraction.
  - deterministic source-backed table evidence evaluation.
  - read-only RAG-ready chunk inspection/export.
  - read-only chunk quality audit.
  - backward-compatible chunk contract hardening v1 for source-backed handoff readiness.
  - backward-compatible table chunk context v1 for source-backed handoff readability.
  - deterministic source location/citation hardening for search/ask/export/audit handoff visibility.
  - fresh splitter cleanup validation on newly processed temporary workspace outputs.
  - service/title/approval/signature table false-positive cleanup v2 for newly processed documents.
  - Stage 33 splitter cleanup validation closure over a 4-document fresh sample.
  - Stage 34.0 deterministic text chunk coherence audit/design for the next bounded implementation.
  - Stage 34.1 deterministic text chunk coherence edge cleanup v1.
  - Stage 34.2 docs-only finite finish roadmap lock after chunk coherence and metric reconciliation.
  - Stage 34.3 unified chunk quality taxonomy/reporting v1.
  - Stage 35 external `Example_data` validation v1 through safe temporary workspace and machine-readable reports.
  - Stage 36 targeted chunk tail sample export and cleanup decision evidence: cleanup not needed now.
  - Stage 37 language-aware OCR smoke/eval and handoff polish for standalone images.
- Not confirmed:
  - scanned PDF OCR;
  - embedded DOCX/PDF image OCR;
  - LLM generation;
  - summarization / draft generation;
  - semantic retrieval;
  - embeddings/vector DB;
  - full RAG;
  - table-aware analytics;
  - external proprietary APIs.

## If time stops now

- run `pytest`;
- run `demo_customer_flow`;
- check README limitations;
- make sure storage artifacts are not committed.

## Final delivery preparation lock

Stage 38 is the final delivery preparation route after completed Stage 37.1. It is fixed and should not expand without a separate decision.

- Stage 38.0 Final delivery preparation plan lock: docs-only route lock; no code/tests/storage/runtime/external artifacts.
- Stage 38.1 Metrics & acceptance criteria documentation: define ETL/RAG-readiness metrics and acceptance criteria in `docs/project/METRICS_AND_ACCEPTANCE.md`, including processing, chunk, table, retrieval/QA, OCR smoke and operational quality gates.
- Stage 38.2 Single-file structure inspector: CLI inspection/handoff tool for one arbitrary file, processing only in a temporary workspace and reporting sections/blocks/chunks/tables/images/warnings without production storage pollution.
- Stage 38.3 Operation manuals: completed docs-only in `docs/project/OPERATION_GUIDE.md` with short, medium and detailed operation instructions for the confirmed baseline.
- Stage 38.4 Language/comment audit & polish: audit first, then safe translation/polish of comments/docs/help text; keep API/JSON/CLI identifiers, test names and technical symbols unchanged.
- Stage 38.5 Experiments packaging: explain repository experiments/evaluation flows, scripts linkage and external dataset path-only policy; do not add fake notebook experiments.
- Stage 38.6 Final cleanup & verification checklist: full pytest, demo smoke, API smoke, OCR smoke, external validation smoke, single-file inspector smoke after Stage 38.2, UTF-8 sanity, `git diff --check`, cleanup runtime artifacts, known limitations and next development steps, and final acceptance checklist.

Known limitations and next development steps are part of final delivery preparation, not an optional afterthought. The final acceptance checklist is also part of Stage 38.6 and should use `docs/project/METRICS_AND_ACCEPTANCE.md` as the metrics/acceptance baseline.

Local physical copy of the project should be made only after runtime artifacts are cleaned and `git status --short` is clean.

Cleanup of the local project folder must not remove source files, tests, docs, `first_test_data` or tracked baseline files.

## Next choice

The next direction is selected and finite after Stage 37.1. Keep future work bounded to source-backed/evaluation-visible improvements; Stage 38.0 locks final delivery preparation before Stage 38.1 starts.

Follow-up sequence:

- Stage 33.0 docs-only splitter roadmap realignment after manual chunk review, completed.
- Stage 33.1 Splitter structure cleanup v1, completed.
- Stage 33.2 Fresh splitter cleanup validation on temporary workspace, completed.
- Stage 33.3 Service table false-positive cleanup v2, completed.
- Stage 33.4 Splitter cleanup validation closure docs, completed.
- Stage 34.0 Text chunk coherence audit & implementation plan, completed.
- Stage 34.1 Text chunk coherence / chunk packing v1, completed.
- Stage 34.2 Finite finish roadmap lock after chunk coherence, completed docs-only.
- Stage 34.3 Chunk quality taxonomy normalization/reporting v1, completed.
- Stage 35 External `Example_data` validation v1, completed as evidence over explicit temporary workspace; external data is not training data and is not committed.
- Stage 36 Targeted external chunk tail inspection / cleanup decision v1, completed; cleanup not needed now based on local sample evidence.
- Stage 37 Optional light OCR handoff polish, completed.
- Stage 38.0 Final delivery preparation plan lock, completed / docs-only.
- Stage 38.1 Metrics & acceptance criteria documentation, completed / docs-only.
- Stage 38.2 Single-file structure inspector, completed.
- Stage 38.3 Operation manuals, completed / docs-only.
- QA evaluator retrieval-loop speed/cache moves to later/backlog only if it becomes a severe operational blocker.

This preserves the delivery-first rule: every stage should be demo-ready / shippable, future stages can be dropped without breaking the current baseline, large architecture rewrites stay out of scope, and future AI capabilities remain source-backed / evaluation-visible.

Stage 29.1 and Stage 29.2 closed visibility/export/audit for chunks. Stage 30 completed the first production-contract hardening step for chunk payload/source context, Stage 31 improved table chunk readability, and Stage 32 strengthened source location/citation hints for future source-backed handoff, without claiming full RAG readiness or table analytics.

Current chunks are acceptable for lexical search and now carry stronger source/location/citation metadata. Newly processed chunks also have cleaner splitter structure after Stage 33.1 and fewer approval/signature table false positives after Stage 33.3.
Stage 33.2 adds a bounded validation workflow for proving cleanup on fresh temporary outputs, without migrating old `storage/results`. Stage 33.4 records an expanded 4-document fresh validation run with zero failures/warnings, so Stage 33 is closed from the splitter cleanup standpoint.
Stage 34.1 implements the narrow ordinary text chunk coherence cleanup target without full RAG or semantic retrieval.
Stage 34.2 locks the finite finish route, Stage 34.3 implements metric taxonomy normalization before any additional cleanup, Stage 35 validates the external `Example_data` path without committing external/runtime artifacts, Stage 36 closes the targeted compact tail cleanup decision as no cleanup needed now, and Stage 37 closes the optional OCR handoff polish.

Known splitter issues:

- heading-only / short chunks are reduced but not semantically eliminated;
- TOC / оглавление no longer intentionally acts as parent for real content in newly processed structure;
- duplicate heading text is cleaned only for safe normalized-identical heading repeats;
- obvious short, compact and single-cell service/title/approval/signature table-like blocks are demoted conservatively, but unusual layouts can still require review;
- DOCX page metadata can be unavailable, so page context must not be invented.
- Stage 33.2 treats null DOCX page metadata as an expected limitation, not a failure.
- Existing processed JSON is not migrated; cleanup improvements apply to newly processed documents.
- Text chunk packing changes can affect lexical scoring/snippet exactness; Stage 34.1 kept the change conservative, but future ranking-sensitive work should compare search/demo outputs carefully.
- Remaining compact chunks after Stage 34.1 are categorized as title/cover fragments, TOC/list fragments, formula/calculation micro-sections and pollutant/equipment micro-evidence; confirmed real problematic low-value tails were `0` in the inspected exact sample.
- Stage 34.3 formalizes this in audit reporting: raw `content_type` counts, table-linked counts and strict `table_row` counts are separate; compact `<250` chunks are evidence taxonomy, not automatic defects.
- No endless splitter polishing: cleanup v2 is not allowed unless non-empty Stage 35 external evidence shows repeated real problems.

Do not present full RAG, LLM generation, embeddings/vector DB, semantic retrieval/reranking, scanned PDF OCR, embedded DOCX/PDF OCR, speed/cache work, table analytics / SQL-like QA, production UI or external proprietary API as ready or in-scope for the finite finish route.

## Note

- Stage 18 completed the governance / roadmap audit and aligned the project docs with the current code baseline.

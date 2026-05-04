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
- Stage 33 closure evidence: 4-document fresh validation over `first_test_data` passed with `documents_with_failures=0`, `service_table_suspects=0`, and `real_table_chunks=984`.
- Stage 34.0 evidence: fresh temporary audit over 4 explicit sample files found `text_chunks=947`, `table_chunks=5114`, `short_text_chunks=29`, `median_text_chars=884`, and table-heavy outputs dominating the sample; this is design evidence, not a behavior change.
- Stage 34.1 evidence: on the same explicit 4-file fresh sample, `heading_only_chunks=0`, `nonservice_short_text_chunks=21`, `single_paragraph_text_chunks=0`, `one_line_text_chunks=0`, and `real_table_chunks=4008`.
- Stage 34.2 evidence: post-commit exact validation after Stage 34.1 had `documents_processed=4`, `documents_with_failures=0`, `total_chunks=6029`, `toc_parent_violations=0`, `duplicate_heading_violations=0`, `heading_only_chunks=0`, `service_table_suspects=0`, `real_table_chunks=4008`.
- Stage 34.2 metric reconciliation: raw `content_type` counts were `text=921`, `table=1100`, `table_row=4008`; a broad collector counted `234` text chunks with table links as table chunks, producing collector `text=687` and `table=5342`.
- Stage 34.2 short-chunk reconciliation: raw text `<250` gives `57` short / `52` nonservice, while raw text `<120` gives `25` short / `21` nonservice; the apparent growth is taxonomy/threshold mismatch, not a direct Stage 34.1 regression.
- Stage 34.3 reporting makes that reconciliation explicit in JSON/console output: compact `<250` chunks are classified as evidence taxonomy and are not automatic defects; cleanup is reserved for repeated `real_low_value_tail` or other confirmed repeated problems.

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
- Not confirmed:
  - scanned PDF OCR;
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

## Next choice

The next direction is selected and finite after Stage 34.2. Keep future work bounded to source-backed/evaluation-visible improvements; do not start final polish until the explicit command or until the planned stages are completed or intentionally dropped.

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
- Stage 35 External `Example_data` validation v1, next as evidence over explicit temporary workspace; external data is not training data and is not committed.
- Stage 36 Targeted cleanup v2, conditional only if Stage 35 shows repeated real problems.
- Stage 37 Optional light OCR handoff polish, droppable and only if time remains.
- Final delivery preparation after the planned/conditional stages are done or dropped.
- QA evaluator retrieval-loop speed/cache moves to later/backlog only if it becomes a severe operational blocker.

This preserves the delivery-first rule: every stage should be demo-ready / shippable, future stages can be dropped without breaking the current baseline, large architecture rewrites stay out of scope, and future AI capabilities remain source-backed / evaluation-visible.

Stage 29.1 and Stage 29.2 closed visibility/export/audit for chunks. Stage 30 completed the first production-contract hardening step for chunk payload/source context, Stage 31 improved table chunk readability, and Stage 32 strengthened source location/citation hints for future source-backed handoff, without claiming full RAG readiness or table analytics.

Current chunks are acceptable for lexical search and now carry stronger source/location/citation metadata. Newly processed chunks also have cleaner splitter structure after Stage 33.1 and fewer approval/signature table false positives after Stage 33.3.
Stage 33.2 adds a bounded validation workflow for proving cleanup on fresh temporary outputs, without migrating old `storage/results`. Stage 33.4 records an expanded 4-document fresh validation run with zero failures/warnings, so Stage 33 is closed from the splitter cleanup standpoint.
Stage 34.1 implements the narrow ordinary text chunk coherence cleanup target without full RAG or semantic retrieval.
Stage 34.2 locks the finite finish route, and Stage 34.3 implements metric taxonomy normalization before any additional cleanup.

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
- No endless splitter polishing: cleanup v2 is not allowed unless Stage 35 external evidence shows repeated real problems.

Do not present full RAG, LLM generation, embeddings/vector DB, semantic retrieval/reranking, scanned PDF OCR, embedded DOCX/PDF OCR, speed/cache work, table analytics / SQL-like QA, production UI or external proprietary API as ready or in-scope for the finite finish route.

## Note

- Stage 18 completed the governance / roadmap audit and aligned the project docs with the current code baseline.

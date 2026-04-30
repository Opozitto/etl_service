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

Next recommended: Stage 31 Table chunk context v1.

Follow-up sequence:

- Stage 32 Source location/citation hardening.
- Stage 33 QA evaluator retrieval-loop speed/cache, optional/later and only if speed becomes a blocker after chunk inspection/export and quality audit.
- Final polish checkpoint starts only by explicit user command: "стоп, следующий шаг делаем финал".

This preserves the delivery-first rule: every stage should be demo-ready / shippable, future stages can be dropped without breaking the current baseline, large architecture rewrites stay out of scope, and future AI capabilities remain source-backed / evaluation-visible.

Stage 29.1 and Stage 29.2 closed visibility/export/audit for chunks. Stage 30 completed the first production-contract hardening step for chunk payload/source context so future source-backed RAG handoff can rely on stronger units, without claiming full RAG readiness.

Current chunks are acceptable for lexical search and now stronger as source-backed handoff units. The next priority is table chunk context and source location/citation hardening, not another diagnostic script and not speed/cache.

Do not present LLM/RAG, scanned PDF OCR, OCR for scanned PDFs, or table analytics as ready.

## Note

- Stage 18 completed the governance / roadmap audit and aligned the project docs with the current code baseline.

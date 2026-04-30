# FINISH_LINE

## Delivery-first finish strategy

- The roadmap now stays delivery-first: every next stage should leave the project demo-ready / shippable on its own.
- Future stages may be dropped without breaking the current baseline.
- Any future AI capability should remain source-backed and evaluation-visible.
- Large architecture rewrites stay out of scope unless there is a separate decision.

## Current baseline

- ETL baseline runs end-to-end in the confirmed local environment.
- Supported document formats: `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`.
- Standalone `jpg` / `jpeg` / `png` are accepted only in metadata-only mode without OCR.
- `HEIC` / `HEIF` / `TIFF` / `TIF` / `BMP` / `WEBP` remain unsupported image-like formats.
- `XLS` and `XLSX` are extracted into JSON, flow into chunks/search/ask, and use flattened lexical retrieval.
- Row-level chunks for tables add `sheet` / `table` / `row` / `column-value` context, but this is still lexical retrieval, not table-aware analytics.
- Customer demo smoke runner is available as a read-only CLI helper and honestly shows the current baseline limitations.

## Best shippable baseline

- supported formats: `pdf`, `doc`, `docx`, `rtf`, `txt`, `xlsx`, `xls`.
- source-backed search/ask with explicit evidence.
- spreadsheet table retrieval with row-level lexical context.
- audit/demo runner for corpus visibility and customer flow.
- image intake metadata-only without OCR.

## What is confirmed, and what is not

- Confirmed:
  - source-backed search;
  - source-backed ask / extractive QA;
  - corpus audit visibility;
  - corpus rebuild;
  - spreadsheet table retrieval with row-level context.
- Not confirmed:
  - OCR;
  - LLM generation;
  - summarization / draft generation;
  - semantic retrieval;
  - vector DB;
  - full RAG;
  - table-aware analytics;
  - external proprietary APIs.

## If time stops now

- run `pytest`;
- run `demo_customer_flow`;
- check README limitations;
- make sure storage artifacts are not committed.

## Next choice

Next recommended: Stage 19.1 OCR candidate reporting, not production OCR.

## Note

- Stage 18 completed the governance / roadmap audit and aligned the project docs with the current code baseline.

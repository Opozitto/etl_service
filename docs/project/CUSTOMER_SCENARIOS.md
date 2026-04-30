# CUSTOMER SCENARIOS

## Goal of Stage 10

Capture customer scenarios and an evaluation set for the pilot track before Stage 11-17 sharpen ask / OCR / tables / summarization / integration. This is a docs-level baseline that connects the current local ETL/search/evaluation foundation to real ecologist workflows.

## Main user

Main user: ecologist-planner.

He works with client source files, normative documents, project documentation, templates, and methodological materials. For him, source-backed search, extractive QA, requirements extraction, calculation inputs, and corpus quality control are critical.

## MVP / pilot scenarios

All pilot scenarios below remain source-backed. They may use existing corpus content and audit visibility, but they do not imply generated answers or ungrounded synthesis.

### S1. Source-backed search

The user searches for fragments or sections in client or normative documents.

Expected output:

- list of found documents / chunks;
- `file` / `document_id`;
- `section_title`;
- `snippet`;
- `score` / `rank`.

### S2. Source-backed extractive QA

The user asks a question about uploaded documents.

Expected output:

- a short answer strictly grounded in found sources;
- links to `file` / `document_id` / `chunk` / `section`;
- if no data exists, an explicit `нет информации в корпусе`.

### S3. Requirements extraction

The user asks to find requirements or normative conditions.

Expected output:

- found requirements as extractive snippets;
- source references;
- candidate category / score / matched terms where available;
- no generation of new requirements and no legal/compliance guarantee.

### S4. Calculation inputs discovery

The user searches for data needed for calculations or justifications.

Expected output:

- found numeric and text fragments;
- source references;
- candidate tables with headers, preview rows, category/tags, score, and matched terms where available;
- a note if tables or OCR are required.

### S5. Document quality / audit

The user or developer checks whether the corpus is fit for use.

Expected output:

- batch report;
- corpus audit;
- retrieval eval;
- problem documents.

### S6. OCR / image intake candidate

A scan or photo of a document.

Current output:

- metadata-only fallback when no local OCR engine is available;
- OCR candidate detection / reporting;
- optional local OCR baseline for standalone `jpg` / `jpeg` / `png` when the engine is available;
- do not promise ready scanned PDF OCR.

Future path:

- scanned PDF OCR remains out of scope;
- table/table-layout OCR and full document layout analysis remain out of scope.

### S7. Summarization / draft generation candidate

The user asks for a summary or a draft section.

Expected output at the current stage:

- future spike only;
- do not promise LLM generation as ready.

## Out of scope for Stage 10

Currently out of scope:

- production OCR;
- semantic retrieval;
- vector DB;
- full RAG;
- LLM generation / answer synthesis;
- automatic generation of documentation fragments;
- promise of HEIC as a ready intake path;
- promise of XLS/XLSX table intelligence beyond the current baseline;
- external proprietary APIs.

## Expected results

Stage 10 should record not a functional implementation, but a pilot track contract:

- user scenarios;
- expected outputs for search, QA, extraction, and audit;
- limitations of the current baseline;
- minimal evaluation set;
- links to future stages.

## Acceptance criteria

- Scenarios are formulated for the ecologist-planner, not for an abstract user.
- Each MVP / pilot scenario has an expected result tied to source-backed behavior.
- Nothing from OCR / RAG / LLM generation is announced as ready unless it is confirmed by code.
- The minimal evaluation set covers supported now / partial / future boundaries.
- The material connects the current Stage 7-9 baseline with Stage 11-17.

## Minimal evaluation set

Below is the minimal set of evaluation cases for Stage 10. It fixes which questions must pass through the current foundation and which ones should remain honestly limited.

| id | scenario | user_question_or_task | input_scope | expected_behavior | expected_sources_required | current_stage_support | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EC-01 | Source-backed search | Find `экология проект` in the corpus | Local corpus index and saved JSON results | Return top hits with `file`, `document_id`, `section_title`, `snippet`, `score` / `rank` | yes | supported now | Basic retrieval proof |
| EC-02 | Requirements search | Find requirements for PДВ / emissions | Documents from client corpus and normative source files | Show extractive snippets with source references | yes | supported now | Requirements must be extracted, not generated |
| EC-03 | Extractive QA | What deadline or condition is stated in the document? | Chunk-level corpus content | Short answer strictly grounded in sources | yes | supported now | If no answer exists, return `нет информации в корпусе` |
| EC-04 | No-answer case | Is there information about X if there is none? | Relevant corpus subset | Explicitly say that the information is absent | yes | supported now | Checks honest refusal without hallucination |
| EC-05 | Calculation inputs | Find source data for a calculation | Text and numeric fragments in docs | Return numbers/fragments and candidate table previews with references | yes | supported now | Stage 23 adds read-only table evidence evaluation; no automatic calculations |
| EC-06 | Audit visibility | A document without chunks should be flagged by audit | Batch corpus outputs and audit report | Appear in problem documents / audit summary | no | supported now | Linked to the Stage 7-9 reporting layer |
| EC-07 | OCR limitation / candidate visibility | A scan or photo of a document | JPG / JPEG / PNG / HEIC candidate inputs | Mark metadata-only fallback, OCR candidates, and optional local OCR baseline for standalone images when engine is available | no | Stage 20 | Do not promise scanned PDF OCR; HEIC/HEIF/TIFF/TIF/BMP/WEBP stay unsupported |
| EC-08 | Table input | XLS / XLSX table-heavy document | Spreadsheet or table-like source | XLS and XLSX are supported at baseline level with flattened lexical retrieval plus read-only table evidence candidates | yes | supported now | Row-level chunks and Stage 23 evidence improve source-backed preview; this is still not table-aware analytics |
| EC-09 | Summarization | Make a short summary of a document | Source document plus request for summary | Future spike only | yes | future | Do not announce ready summarization |
| EC-10 | Draft generation | Prepare a draft section of documentation | Project doc context and task brief | Future spike only | yes | future | Do not announce ready LLM generation |
| EC-11 | Source attribution | Show where the answer came from | Search hits and chunk references | Answer must carry explicit source references | yes | supported now | Trust criterion for the pilot track |
| EC-12 | Problem documents | Find problematic documents in the corpus | Index, manifest, batch and audit reports | Audit should surface duplicates, warnings, missing chunks, and low-quality items | no | supported now | Uses the Stage 7-9 reporting layer |

## Relationship with Stage 11-17

- Stage 11 should prove ask / extractive QA with sources on top of the current corpus, without turning it into generation.
- Stage 12 should test OCR / image intake and separate confirmed support from limitations, especially for scans and phone photos.
- Stage 13 keeps the historical XLS / tables decision; Stage 14 superseded the old unsupported-XLS state with practical baseline support.
- Stage 15 should align customer demo readiness, ingestion-search QA, supported formats, and the scenario matrix after XLS support.
- Stage 16 should treat summarization / draft generation as a future spike, not a baseline claim.
- Stage 17 should connect the confirmed parts into a prototype integration flow while keeping audit and eval visible.
- Stage 19.1 adds OCR candidate reporting and read-only visibility, while Stage 20 adds the optional local OCR baseline for standalone images only.
- Stage 21 adds a separate read-only OCR smoke evaluation script for image readiness checks.
- The Stage 17 demo helper may read the current corpus snapshot, rebuild the index only behind an explicit flag, and show the current baseline honestly.

## Notes on the current baseline

- Stage 7-9 already provide batch reporting, corpus audit, and retrieval quality evaluation.
- This makes source-backed search and source-backed proof the right immediate pilot direction.
- OCR, semantic retrieval, vector DB, RAG, and LLM generation remain outside the confirmed baseline; OCR candidate reporting is the current read-only bridge, and the standalone image OCR baseline is optional / local only.

## Stage 14 note

- EC-08 now reflects practical `.xls` / `.xlsx` support at baseline level.
- The scenario set still uses flattened lexical retrieval and deterministic table evidence, and does not claim full table reasoning.
- Row-level spreadsheet chunks and Stage 23 table evidence improve source-backed table row/value discovery without SQL/table analytics or automatic calculations.

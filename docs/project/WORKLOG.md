# WORKLOG

## done

- Stage 3 closed.
- Stage 4 confirmed through `tests/test_api.py`.
- Stage 5 retrieval proof/demo confirmed.
- Stage 6 README/demo alignment confirmed against the current baseline.
- Stage 7 closed as the batch/evaluation reporting layer.
- Stage 8 closed as the read-only corpus quality audit.
- Stage 9 closed as the retrieval quality mini-evaluation.
- After Stage 9, a roadmap realignment was performed against the extended customer brief.
- Stage 10 customer scenarios and evaluation set created as a docs-only artifact.
- Stage 11 closed as the source-backed ask response alignment.
- Stage 12 partial: explicit unsupported image format contract added for known image-like formats outside `jpg` / `jpeg` / `png`, with user-facing wording localized to Russian.
- Stage 12.2 completed as standalone `jpg` / `jpeg` / `png` image intake smoke/evaluation without OCR.
- Stage 12 closed with API smoke/evaluation for standalone image intake and documentation closure.
- Stage 12 follow-up: added manual image intake sample files `first_test_data/РЎРїСЂР°РІРєР° (С‚Р°Р±Р»РёС†Р°).jpg` and `first_test_data/РЎРїСЂР°РІРєР° (С‚Р°Р±Р»РёС†Р°).png`.
- Code/tests/OCR/dependencies were unchanged in the sample-files follow-up.
- Commits:
  - `6997d98` `Add unsupported image format contract`
  - `83b741b` `Localize unsupported image format message`
  - `26199bd` `Add image intake smoke contract`
  - `0a57c48` `Close Stage 12 image intake contract`
- Checks:
  - `python -m pytest -q tests\test_extractors.py -k "image or registry"` -> Stage 12.2 contract check;
  - `python -m py_compile tests\test_extractors.py` -> OK.
- Commit: `1a02af5` `Add source-backed ask response`.
- Checks:
  - `python -m pytest -q tests\test_api.py` -> 4 passed
  - `python -m pytest -q tests\test_search.py` -> 3 passed
  - `python -m py_compile app\schemas\api.py app\search\index.py tests\test_api.py` -> OK
- Storage changes after `test_api` were cleaned before commit.
- `git status --short` after commit was clean.
- Stage 19.0 added as a docs-only roadmap lock to keep the project delivery-first.

## next

- Stage 19.1 OCR candidate reporting / OCR-readiness, without production OCR.
- Stage 19.2 Customer demo finalization / final polish checkpoint.
- Stage 20 Local OCR baseline for jpg/png, only if time allows.
- Stage 21 OCR quality evaluation, only after OCR baseline.
- Stage 22 Requirements extraction v1, source-backed, no generation.
- Stage 23 Table-aware evaluation / calculation inputs v2.
- Stage 24 Summarization / draft generation spike, only if source-backed foundation remains stable.

## alignment

- Stage 7-9 are the quality/evaluation foundation of the project.
- That foundation covers part of the brief about solution quality evaluation.
- The next phase is the pilot AI-service track for ecologists, not a claim that OCR, RAG, or LLM generation are already ready.
- Stage 19.0 locks the roadmap so future stages remain shippable and independently valuable.

## risks

- `XLS` and `XLSX` are still baseline spreadsheet inputs.
- Spreadsheet retrieval remains lexical; improvement comes from row-level context, not table-aware analytics.
- OCR is not implemented.
- `HEIC` / `HEIF` / `TIFF` / `TIF` / `BMP` / `WEBP` remain unsupported.
- LLM / RAG / generation are not implemented.
- The main current risk is not a lack of ideas, but scope creep into OCR / RAG / LLM work before the foundation is stable.
- Full `pytest` inside the Codex sandbox on Windows can still hit `PermissionError` in pytest temp / `tmp_path`, even though the local `etl_env` run works.
- `PermissionError` in the Codex sandbox remains an environment limitation, not a project defect.

## decisions

- `python -m pytest -q` without activating `etl_env` is not a valid project check, because it may use base Anaconda and miss dependencies like `httpx`.
- The source of truth for pytest regression remains:
  - `conda run -n etl_env python -m pytest -q`
  - or `python -m pytest -q` only after `conda activate etl_env`
- Codex sandbox ACL limits on Windows are treated as environment limitations, not a reason to change code or tests.
- Stage 19.1 must stay OCR candidate reporting, not production OCR.
- Stage 20 OCR baseline is allowed only after Stage 19.1 and a separate decision.

## open questions

- `не подтверждено`: whether future work is needed for true table-aware reasoning beyond the current flattened retrieval baseline.

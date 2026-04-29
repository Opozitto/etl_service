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
- Stage 12 partial: explicit unsupported image format contract added for known image-like formats outside `jpg`/`jpeg`/`png`, with user-facing wording localized to Russian.
- Stage 12.2 completed as standalone `jpg`/`jpeg`/`png` image intake smoke/evaluation without OCR.
- Stage 12 closed with API smoke/evaluation for standalone image intake and documentation closure.
- Stage 12 follow-up: added manual image intake sample files `first_test_data/Справка (таблица).jpg` and `first_test_data/Справка (таблица).png`.
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

## next

- Stage 13 closed as the historical XLS / tables baseline decision; Stage 14 later superseded the unsupported-XLS state.

## alignment

- Stage 7–9 are now treated as the quality/evaluation foundation for the project.
- That foundation covers the part of the brief about quality assessment of solutions.
- The next phase is a pilot AI-service track for ecologists/design engineers, not a claim that OCR, RAG, or LLM generation is already ready.

## risks

- `.XLS` is now baseline-supported through Stage 14; `.XLSX` remains supported baseline spreadsheet input.
- Spreadsheet retrieval is still lexical; the quality gain comes from row-level chunks, not from table-aware analytics.
- OCR is not implemented.
- `HEIC` is not confirmed.
- LLM / RAG / generation are not implemented.
- Full `pytest` inside the Codex sandbox on Windows can still hit `PermissionError` in pytest temp / `tmp_path`, even though the local `etl_env` run works.
- Codex sandbox `PermissionError` remains an environment limitation, not a project defect.

## decisions

- `python -m pytest -q` without activating `etl_env` is not a valid project check because it may use base Anaconda and miss dependencies such as `httpx`.
- The source of truth for pytest regression remains:
  - `conda run -n etl_env python -m pytest -q`
  - or `python -m pytest -q` only after `conda activate etl_env`
- Codex sandbox ACL limitations on Windows are treated as environment constraints, not as a reason to change code or tests.
- Stage 3 remains closed without workaround changes in code or tests.

## open questions

- `не подтверждено`: whether future work should add true table-aware reasoning beyond the current flattened retrieval baseline.


- Stage 14 completed as practical XLS baseline support.
- Stage 16 table retrieval quality improvement completed for spreadsheet row-level lexical chunks with column/value context.
- Local full pytest result: `conda run -n etl_env python -m pytest -q --basetemp=D:\Projects\etl_service\.pytest-run-temp\stage14` -> `39 passed in 14.16s`
- Runtime artifacts after local pytest were restored and must not be committed.
- Stage 15 next: customer demo readiness / docs and scenario alignment.
- Checks passed in `etl_env`:
  - `python -m py_compile app\pipeline\errors.py app\pipeline\extractors\registry.py app\pipeline\extractors\xls.py app\pipeline\extractors\xlsx.py app\pipeline\transform\structure.py app\services\document_service.py app\search\index.py app\search\store.py tests\test_extractors.py tests\test_api.py`
  - `python -m pytest -q tests\test_extractors.py -k "xls or xlsx or table or image"`
  - `python -m pytest -q tests\test_api.py -k "xls or table or process or search or ask"`

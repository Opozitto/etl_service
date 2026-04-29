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
- Commit: `1a02af5` `Add source-backed ask response`.
- Checks:
  - `python -m pytest -q tests\test_api.py` -> 4 passed
  - `python -m pytest -q tests\test_search.py` -> 3 passed
  - `python -m py_compile app\schemas\api.py app\search\index.py tests\test_api.py` -> OK
- Storage changes after `test_api` were cleaned before commit.
- `git status --short` after commit was clean.

## next

- Stage 12 — OCR / image intake spike.

## alignment

- Stage 7–9 are now treated as the quality/evaluation foundation for the project.
- That foundation covers the part of the brief about quality assessment of solutions.
- The next phase is a pilot AI-service track for ecologists/design engineers, not a claim that OCR, RAG, or LLM generation is already ready.

## risks

- `.XLS` decision is still not closed, and table support remains only partially defined.
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

- `не подтверждено`: whether `.XLS` should be documented separately as a legacy input beyond the current Stage 2 baseline.

# Language/comment audit

## Назначение

Stage 38.4 проверяет, не мешают ли англоязычные comments, docstrings, help text, console output и docs fragments русскоязычной финальной сдаче проекта.

Audit был ограничен безопасным delivery scope: `app`, `scripts`, `tests`, `README.md` и `docs/project`. External dataset, production `storage`, `.runtime_eval`, `.pytest-run-temp`, `.deps` и historical runtime artifacts не рассматривались как кандидаты для правок.

## Что проверялось

- Python comments/docstrings в `app`, `scripts`, `tests`.
- `argparse` descriptions/help strings в project scripts.
- Console output strings в user/demo/evaluation scripts.
- README и `docs/project/*.md`.
- Dangerous readiness wording: проверялись точные фразы, которые могли бы ошибочно заявить готовность `full RAG`, `LLM generation`, `semantic retrieval`, `vector DB`, `scanned PDF OCR`, `embedded image OCR` или `table analytics`.

## Audit categories

### safe_to_polish

Безопасными для полировки признаны:

- FastAPI `description`, потому что это user-facing описание сервиса, а не API contract.
- CLI `argparse` descriptions/help text в selected scripts.
- Console labels в scripts, которые выводятся человеку при manual smoke/eval.
- Короткие управляющие docs updates для Stage 38.4.

### keep_as_technical_identifier_or_contract

Осознанно оставлено на английском:

- API route paths и HTTP method names.
- JSON/report field names: например `status`, `summary`, `report_version`, `results_dir`, `source_filename`, `chunk_quality_status`.
- CLI option names: например `--results-dir`, `--json-report-path`, `--max-documents`, `--language`.
- Module/function/class/test/fixture names.
- Stage names, commit names, report version identifiers и taxonomy bucket names.
- Technical terms, где перевод ухудшает точность: `source-backed`, `baseline`, `handoff`, `read-only`, `workflow`, `full RAG`, `LLM generation`, `semantic retrieval`, `embeddings/vector DB`, `table analytics`.
- Exact command examples and CLI snippets.

### historical_log_do_not_touch

Не трогались:

- Historical command logs and old stage notes in `docs/project/WORKLOG.md`.
- Historical decisions and stage context, where English words document фактический прошлый state.
- Existing command outputs/examples, если они отражают machine-readable или исторический CLI/report contract.

### out_of_scope_or_risky

Не переводились:

- Third-party dependency files under `.deps`.
- Runtime/temp directories and reports.
- External `D:\Projects\etl_service_backup\Example_data`.
- Production `storage/index`, `storage/results`, `storage/uploads`.
- Exception messages or output strings that might be used by tests/contracts unless they were clearly human-facing and low-risk.

## Что исправлено

- Локализовано FastAPI описание сервиса в `app/main.py`.
- Полированы selected CLI/help/console strings в:
  - `scripts/check_ocr.py`;
  - `scripts/cleanup_storage.py`;
  - `scripts/extract_requirements.py`;
  - `scripts/evaluate_tables.py`;
  - `scripts/audit_rag_chunks.py`;
  - `scripts/export_rag_chunks.py`.
- Добавлена эта audit summary page.
- Управляющие docs обновлены так, чтобы Stage 38.4 был частью final delivery toolkit.

## Правила будущей локализации

- Переводить только human-facing prose: descriptions, help text, README/docs sentences, explanatory comments/docstrings.
- Не переводить identifiers, field names, flags, report versions, stage names, filenames, module names и test names.
- Не переводить exact command examples и machine-readable report output.
- Не менять behavior ради языка.
- Если строка одновременно видна пользователю и может быть contract для теста/API/report, сначала считать её contract и не менять без отдельного решения.
- Для русскоязычных Markdown сохранять UTF-8 без BOM и без replacement char `U+FFFD`.

## Итог

Stage 38.4 не меняет production behavior, public API, JSON schema, CLI option names, storage layout, runtime artifacts или external dataset policy. Полировка ограничена безопасным user-facing текстом и документацией.

# FINAL DELIVERY CHECKLIST

## Назначение

Этот документ фиксирует финальный checklist для сдачи ETL service.

Stage 38.6 - это не новый feature stage. Это проверка упаковки, чистоты локальной папки, честности ограничений и готовности к физической копии проекта.

Stage 39.0 добавляет post-audit triage lock после deep audit `first_test_data`: проект находится в bounded remediation before delivery, а не в active feature development. Route конечный: Stage 39.1 standalone OCR safety gate, Stage 39.2 extractor garbage detection, Stage 39.3 final post-audit verification & docs alignment, затем только final delivery preparation.

## Current final delivery package

В текущем репозитории есть:

- приложение / API для обработки документов, локального search и source-backed ask;
- `scripts` для batch/demo/audit/evaluation/inspection workflows;
- `tests` как regression baseline;
- проектная документация в `docs/project`;
- operation guide: `docs/project/OPERATION_GUIDE.md`;
- metrics/acceptance baseline: `docs/project/METRICS_AND_ACCEPTANCE.md`;
- experiments README: `experiments/README.md`;
- language audit: `docs/project/LANGUAGE_AUDIT.md`;
- customer scenarios: `docs/project/CUSTOMER_SCENARIOS.md`;
- single-file inspector: `scripts.inspect_document_structure`;
- known limitations, зафиксированные в README, operation guide, metrics/acceptance и этом checklist.
- post-audit Stage 39.0 classification: bounded remediation separated from accepted deterministic ETL limitations.

## Final verification sequence

Выполнять финальную проверку в локальном `etl_env`. В Codex sandbox full pytest не запускать, если этап docs-only.

1. Проверить чистоту repository:

```powershell
git status --short
```

2. Запустить full regression в обычном локальном окружении:

```powershell
conda run -n etl_env python -m pytest -q
```

3. Запустить customer demo smoke:

```powershell
conda run -n etl_env python -m scripts.demo_customer_flow
```

4. Проверить single-file inspector на маленьком sample-файле с output под `.runtime_eval`:

```powershell
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\small_sample.docx" --output-path .runtime_eval\inspect_report.md --json-report-path .runtime_eval\inspect_report.json --clean-workspace
```

5. Проверить local OCR engine/languages:

```powershell
conda run -n etl_env python -m scripts.check_ocr
```

6. Optional OCR eval для standalone images, если Tesseract и language packs доступны:

```powershell
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path .runtime_eval\ocr_smoke_report.json --language rus+eng
```

Для русского OCR baseline рекомендуемый режим - `--language rus+eng`. OCR без RU language config не считается quality baseline: он может дать misleading латинизированный или искаженный русский текст и допустим только как smoke/best-effort behavior.

7. Optional external validation bounded smoke, если доступен external `Example_data`:

```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --source-scope all-supported --ambiguous-policy all --process --run-eval --run-chunk-quality --clean-workspace --max-documents 10 --max-questions 20
```

External `Example_data` является path-only dataset outside repository. Его не копировать в repository и не коммитить.

8. Если demo/eval/API smoke изменили production storage, восстановить tracked baseline:

```powershell
git restore storage/index storage/results storage/uploads
```

9. Проверить diff whitespace:

```powershell
git diff --check
```

10. Проверить UTF-8 sanity для измененных Markdown-файлов:

```powershell
$files = @(
  'README.md',
  'docs/project/FINAL_DELIVERY_CHECKLIST.md',
  'docs/project/OPERATION_GUIDE.md',
  'docs/project/METRICS_AND_ACCEPTANCE.md',
  'docs/project/FINISH_LINE.md',
  'docs/project/PLAN.md',
  'docs/project/WORKLOG.md',
  'docs/project/CUSTOMER_SCENARIOS.md',
  'experiments/README.md'
)
foreach ($file in $files) {
  $bytes = [System.IO.File]::ReadAllBytes($file)
  $text = [System.Text.Encoding]::UTF8.GetString($bytes)
  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) { throw "BOM found: $file" }
  if ($text.Contains([char]0xFFFD)) { throw "Replacement char found: $file" }
}
```

11. Проверить storage/runtime pollution:

```powershell
git status --short storage/index storage/results storage/uploads .runtime_eval
```

Финальная verification считается завершенной, если все обязательные проверки пройдены или конкретно отмечено, какие optional checks сознательно пропущены и почему.

## Post-audit bounded verification

После Stage 39.1–39.2 финальная проверка должна подтвердить только bounded remediation:

- standalone OCR safety gate не позволяет silently считать подозрительный RU OCR output quality baseline без `--language rus+eng`;
- RTF garbage extraction классифицируется как warning/degraded evidence, а не чистый successful extraction;
- PDF `(cid:...)` garbage fragments surfaced through detection/reporting, без OCR fallback и без PDF parser replacement;
- `.doc` converter/dependency issue описан как preflight/accepted limitation, а не production blocker;
- accepted deterministic ETL limitations остаются honest limitations, а не remediation backlog.

Эта проверка не запускает новый feature roadmap и не добавляет Stage 40+.

## Local cleanup before physical copy

### Safe to remove locally

Перед физической копией можно удалить или сознательно исключить из копии:

- `.runtime_eval/`;
- `.pytest-run-temp/`;
- `.pytest_cache/`;
- `__pycache__/`;
- `.mypy_cache/`, если существует;
- temporary reports, generated by local smoke/eval;
- explicit temporary workspaces, созданные для inspection/evaluation.

### Do not remove

Не удалять при cleanup:

- `.git/`;
- source code;
- `tests`;
- `docs`;
- `experiments/README.md`;
- `first_test_data`;
- tracked baseline storage files, unless intentionally regenerated/restored;
- README/spec/docs;
- `pyproject.toml` и другие config files.

External `D:\Projects\etl_service_backup\Example_data` остается вне repository. Его не копировать в repository и не включать в physical project copy как часть репозитория.

## Physical copy rule

Физическую копию проекта делать только после:

- `git status --short` clean;
- runtime dirs удалены locally или сознательно исключены из копии;
- production storage restored после demo/eval/API smoke;
- нет untracked generated files;
- final checks completed or intentionally skipped with note.

Нельзя копировать/коммитить:

- `.runtime_eval`;
- `.pytest-run-temp`;
- generated JSON/Markdown reports from smoke/eval;
- external `D:\Projects\etl_service_backup\Example_data`;
- external QA file из `Example_data`;
- production storage pollution from local smoke/eval.

Можно копировать/коммитить:

- source code;
- tests;
- docs;
- README/spec/config files;
- `experiments/README.md`;
- `first_test_data`;
- tracked baseline files, если `git status --short` clean.

## Known limitations

- No scanned PDF OCR.
- No embedded image OCR inside DOCX/PDF.
- No advanced OCR pipeline.
- No full RAG.
- No LLM generation.
- No semantic retrieval/reranking/vector DB.
- No table analytics/calculations.
- Optional local OCR only for standalone `jpg`/`jpeg`/`png`.
- For Russian standalone OCR baseline use `--language rus+eng`; OCR without RU language config is smoke/best-effort only.
- DOCX page metadata may be unavailable.
- Deterministic chunking is not semantic document understanding.
- RTF/PDF extraction may require garbage detection/reporting for misleading successful-looking output.
- `.doc` conversion can depend on local converter/dependency environment; this is a preflight limitation unless separately changed.
- Accepted deterministic ETL limitations: missing DOCX pages, formula-like heading fragments, compact pollutant/equipment evidence, isolated table-layout tails, approval/signature service structures and partial multirow header limitations.
- External QA source ambiguity is dataset/workflow diagnostic, not an automatic project failure and not successful quality evidence by itself.

## Bounded route before delivery

Allowed next steps are finite and closing:

- Stage 39.1 standalone OCR safety gate;
- Stage 39.2 extractor garbage detection;
- Stage 39.3 final post-audit verification & docs alignment;
- final delivery preparation only.

Not planned in this route:

- scanned PDF OCR;
- embedded DOCX/PDF OCR;
- semantic retrieval;
- reranking;
- vector DB;
- full RAG;
- advanced OCR pipeline;
- large splitter rewrites;
- endless cleanup/polish.

## Final acceptance checklist

- [ ] Repository clean: `git status --short` has no output.
- [ ] Tests pass in local `etl_env`.
- [ ] Demo pass: `scripts.demo_customer_flow`.
- [ ] API documented.
- [ ] Operation guide present.
- [ ] Metrics doc present.
- [ ] Experiments README present.
- [ ] Single-file inspector present.
- [ ] Limitations honest.
- [ ] Stage 39 post-audit bounded remediation classified and finite.
- [ ] External dataset not committed.
- [ ] Runtime artifacts not committed.
- [ ] No false readiness claims.
- [ ] Final physical copy ready.

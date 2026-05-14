# FINAL DELIVERY CHECKLIST

## Назначение

Этот документ фиксирует финальный checklist для сдачи ETL service.

Checklist предназначен для финальной упаковки, проверки чистоты локальной папки, честности ограничений и готовности к физической копии проекта. Он не описывает историю разработки и не открывает новый feature roadmap.

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
- clear repository baseline: готовые `storage/index`, `storage/results` и `storage/uploads` не коммитятся; они создаются локально после processing.

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

3. Запустить focused regression для OCR/extractor quality checks:

```powershell
conda run -n etl_env python -m pytest -q tests\test_ocr_quality.py tests\test_extraction_quality.py
conda run -n etl_env python -m pytest -q tests\test_extractors.py -k "standalone_image_with_ocr or suppresses_degraded_standalone_ocr_text"
```

4. Запустить relevant focused `py_compile` для OCR/extractor quality path:

```powershell
conda run -n etl_env python -m py_compile app\pipeline\ocr.py app\services\document_service.py app\pipeline\extractors\quality.py app\pipeline\extractors\rtf.py app\pipeline\extractors\pdf.py scripts\evaluate_ocr.py tests\test_ocr_quality.py tests\test_extraction_quality.py tests\test_extractors.py
```

5. Для содержательного customer demo smoke в clear checkout сначала создать локальный sample corpus:

```powershell
conda run -n etl_env python -m scripts.batch_process --input-dir first_test_data --report-path .runtime_eval\last_batch_report.json
```

6. Запустить customer demo smoke:

```powershell
conda run -n etl_env python -m scripts.demo_customer_flow
```

7. Проверить single-file inspector на маленьком sample-файле с output под `.runtime_eval`:

```powershell
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\small_sample.docx" --output-path .runtime_eval\inspect_report.md --json-report-path .runtime_eval\inspect_report.json --clean-workspace
```

8. Проверить local OCR engine/languages:

```powershell
conda run -n etl_env python -m scripts.check_ocr
```

9. Optional OCR eval для standalone images, если Tesseract и language packs доступны:

```powershell
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path .runtime_eval\ocr_smoke_report.json --language rus+eng
```

Для русского OCR baseline рекомендуемый режим - `--language rus+eng`. OCR без RU language config не считается quality baseline: он может дать misleading латинизированный или искаженный русский текст и допустим только как smoke/best-effort behavior.

10. Optional external validation bounded smoke, если доступен external `Example_data`:

```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --source-scope all-supported --ambiguous-policy all --process --run-eval --run-chunk-quality --clean-workspace --max-documents 10 --max-questions 20
```

External `Example_data` является path-only dataset outside repository. Его не копировать в repository и не коммитить.

11. Проверить diff whitespace:

```powershell
git diff --check
```

12. Проверить UTF-8 sanity для измененных Markdown-файлов:

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

13. Проверить storage/runtime pollution:

```powershell
git status --short storage/index storage/results storage/uploads .runtime_eval
git ls-files storage/index storage/results storage/uploads
git check-ignore -v storage/index/probe.json storage/results/probe.json storage/uploads/probe.txt
```

`git ls-files storage/index storage/results storage/uploads` должен быть пустым. `git check-ignore -v ...` должен показывать правила `.gitignore` для всех трех probe-файлов.

14. Проверить, что runtime dirs отсутствуют локально или остаются ignored:

```powershell
git status --short
git check-ignore -v .runtime_eval/probe.json .pytest_cache/probe __pycache__/probe.pyc
```

Если после demo/eval появились `storage/index`, `storage/results`, `storage/uploads` или `.runtime_eval`, их можно удалить вручную как local generated output перед сдачей. Нельзя коммитить эти каталоги или generated reports.

Финальная verification считается завершенной, если все обязательные проверки пройдены или конкретно отмечено, какие optional checks сознательно пропущены и почему.

## Post-audit bounded verification

Финальная проверка должна подтвердить только bounded remediation:

- standalone OCR safety gate не позволяет silently считать подозрительный RU OCR output quality baseline без `--language rus+eng`;
- RTF garbage extraction классифицируется как warning/degraded evidence, а не чистый successful extraction;
- PDF `(cid:...)` garbage fragments surfaced through detection/reporting, без OCR fallback и без PDF parser replacement;
- `.doc` converter/dependency issue описан как preflight/accepted limitation, а не production blocker;
- accepted deterministic ETL limitations остаются honest limitations, а не remediation backlog.

Эта проверка не запускает новый feature roadmap и не расширяет scope перед сдачей.

## Local cleanup before physical copy

### Safe to remove locally

Перед физической копией можно удалить или сознательно исключить из копии:

- `.runtime_eval/`;
- `.pytest-run-temp/`;
- `.pytest_cache/`;
- `__pycache__/`;
- `storage/index/`, `storage/results/`, `storage/uploads/`;
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
- `app/storage`;
- README/spec/docs;
- `pyproject.toml` и другие config files.

External `D:\Projects\etl_service_backup\Example_data` остается вне repository. Его не копировать в repository и не включать в physical project copy как часть репозитория.

## Physical copy rule

Физическую копию проекта делать только после:

- `git status --short` clean;
- runtime dirs удалены locally или сознательно исключены из копии;
- generated runtime storage не попал в tracked files: `git ls-files storage/index storage/results storage/uploads` пустой;
- `.gitignore` подтверждает ignore для `storage/index/probe.json`, `storage/results/probe.json`, `storage/uploads/probe.txt`;
- нет untracked generated files;
- final checks completed or intentionally skipped with note.

Нельзя копировать/коммитить:

- `.runtime_eval`;
- `.pytest-run-temp`;
- generated JSON/Markdown reports from smoke/eval;
- external `D:\Projects\etl_service_backup\Example_data`;
- external QA file из `Example_data`;
- generated `storage/index`, `storage/results`, `storage/uploads` from local smoke/eval.

Можно копировать/коммитить:

- source code;
- tests;
- docs;
- README/spec/config files;
- `experiments/README.md`;
- `first_test_data`;
- project source/docs/tests/configs и `first_test_data`, если `git status --short` clean.

## Known limitations

- Нет scanned PDF OCR.
- Нет embedded image OCR inside DOCX/PDF.
- Нет advanced OCR pipeline.
- Нет full RAG.
- Нет LLM generation.
- Нет semantic retrieval/reranking/vector DB.
- Нет table analytics/calculations.
- Optional local OCR работает только для standalone `jpg`/`jpeg`/`png`.
- Для Russian standalone OCR baseline использовать `--language rus+eng`; OCR без RU language config является только smoke/best-effort режимом.
- OCR safety gate снижает риск misleading-success, но не гарантирует качество OCR.
- DOCX page metadata может быть недоступна.
- Deterministic chunking не является semantic document understanding.
- RTF/PDF garbage detection снижает риск retrieval pollution, но не является RTF/PDF parser rewrite и не добавляет OCR fallback.
- `.doc` conversion может зависеть от local converter/dependency environment; это preflight limitation, если отдельно не изменено.
- Accepted deterministic ETL limitations: missing DOCX pages, formula-like heading fragments, compact pollutant/equipment evidence, isolated table-layout tails, approval/signature service structures и partial multirow header limitations.
- External QA source ambiguity является dataset/workflow diagnostic, а не automatic project failure и не successful quality evidence by itself.

## Delivery-only route

Feature work закрыт. Разрешённые следующие шаги относятся только к сдаче:

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
- [ ] OCR safety gate tests pass: `tests\test_ocr_quality.py` and focused image OCR extractor checks.
- [ ] Extractor quality tests pass: `tests\test_extraction_quality.py`.
- [ ] Focused `py_compile` for OCR/extractor quality path passes.
- [ ] Demo pass: `scripts.demo_customer_flow`.
- [ ] Optional standalone OCR smoke with `--language rus+eng` is either passed or explicitly skipped because local Tesseract/language packs are unavailable.
- [ ] API documented.
- [ ] Operation guide present.
- [ ] Metrics doc present.
- [ ] Experiments README present.
- [ ] Single-file inspector present.
- [ ] Limitations honest.
- [ ] Feature route closed; remaining route is final delivery preparation only.
- [ ] External dataset not committed.
- [ ] Runtime artifacts not committed.
- [ ] Production storage/runtime cleanliness checked: `git ls-files storage/index storage/results storage/uploads` пустой, `git check-ignore -v` подтверждает ignore для storage probes, runtime dirs absent or ignored.
- [ ] Meaningful search/demo in a clear checkout is run only after local processing/index build from `first_test_data` or another explicit input route.
- [ ] Нет false readiness claims.
- [ ] Final physical copy ready.

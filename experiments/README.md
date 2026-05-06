# Experiments

## Назначение

Эксперименты в этом проекте - это воспроизводимые scripts/evaluation workflows, а не обучающие notebooks.

Цель раздела - показать, как проверяется ETL/RAG-readiness текущего baseline: extraction, structure, chunks, retrieval, OCR smoke, table evidence и external validation. Проект не обучает LLM, не реализует full RAG и не заявляет готовыми generation, semantic retrieval или vector DB.

Этот каталог не содержит data files, notebooks, generated JSON reports или runtime outputs. Результаты экспериментов должны создаваться только во временных workspace.

## Карта экспериментов / evaluation workflows

### 1. Baseline smoke / regression

Цель: подтвердить, что базовый ETL/API/search контур не сломан.

```powershell
conda run -n etl_env python -m pytest -q
conda run -n etl_env python -m scripts.demo_customer_flow
```

`pytest` является полной regression-проверкой проекта. `scripts.demo_customer_flow` показывает customer-facing smoke текущего baseline: corpus visibility, source-backed search/ask, table/OCR-candidate visibility и known limitations.

### 2. Single-file structure inspection

Цель: посмотреть структуру одного произвольного документа до добавления его в regular corpus flow.

```powershell
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\file.docx"
conda run -n etl_env python -m scripts.inspect_document_structure --input-path "D:\path\file.docx" --output-path .runtime_eval\inspect_report.md --json-report-path .runtime_eval\inspect_report.json --clean-workspace
```

Workflow показывает metadata, processing info, sections, blocks, chunks, tables, images, warnings и workspace artifacts. Markdown/JSON report пишется только по explicit path, обычно под `.runtime_eval`.

### 3. Corpus audit

Цель: проверить качество saved corpus, problem documents и OCR candidates без изменения production behavior.

```powershell
conda run -n etl_env python -m scripts.audit_corpus
conda run -n etl_env python -m scripts.audit_corpus --report-path .runtime_eval\corpus_audit.json
```

Скрипт читает уже сохраненные JSON/results/index и печатает summary. JSON report является generated runtime artifact и не коммитится.

### 4. RAG-ready chunk export / audit

Цель: увидеть chunk handoff layer: compact taxonomy, table context, source/citation metadata и limitations для будущего source-backed слоя.

```powershell
conda run -n etl_env python -m scripts.export_rag_chunks --max-documents 1 --max-chunks-per-document 5
conda run -n etl_env python -m scripts.audit_rag_chunks --max-documents 1 --max-chunks-per-document 5
conda run -n etl_env python -m scripts.audit_rag_chunks --output-path .runtime_eval\rag_chunk_audit.json --include-samples --sample-limit 5
```

Это visibility/audit слой для chunks, а не embeddings/vector DB, semantic retrieval или full RAG implementation.

### 5. QA / retrieval readiness

Цель: оценить source-backed retrieval/QA readiness по QA dataset и уже обработанным JSON.

```powershell
conda run -n etl_env python -m scripts.evaluate_qa_dataset --qa-path "D:\path\qa.csv"
conda run -n etl_env python -m scripts.evaluate_qa_dataset --qa-path "D:\path\qa.csv" --skip-answer-overlap --json-report-path .runtime_eval\qa_fast_smoke.json
```

Основные метрики: `hit@1`, `hit@3`, `hit@5`, `source_hit_rate`, `evidence_overlap` и optional `answer_overlap`.

`--skip-answer-overlap` - fast smoke mode: он быстрее проверяет retrieval/source visibility и пропускает answer-overlap слой. Для сравнения answer-overlap trend нужен обычный/full evaluator mode.

### 6. External Example_data validation

Цель: воспроизводимо проверить baseline на external `Example_data` как path-only evidence dataset, не копируя его в repository.

Strict expected-source mode:

```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --process --run-eval --run-chunk-quality --clean-workspace
```

Exploratory bounded all-supported / ambiguous-policy all mode:

```powershell
conda run -n etl_env python -m scripts.validate_external_example_data --dataset-dir D:\Projects\etl_service_backup\Example_data --qa-path "D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv" --source-scope all-supported --ambiguous-policy all --process --run-eval --run-chunk-quality --clean-workspace --max-documents 10 --max-questions 20
```

Все reports/workspaces должны оставаться под `.runtime_eval` или explicit temporary path. External dataset и QA file не копируются и не коммитятся.

### 7. OCR smoke

Цель: проверить optional local OCR baseline для standalone image files.

```powershell
conda run -n etl_env python -m scripts.check_ocr
conda run -n etl_env python -m scripts.evaluate_ocr --input-dir first_test_data --json-report-path .runtime_eval\ocr_smoke_report.json --language rus+eng
```

Scope: standalone `jpg`, `jpeg`, `png` only. Scanned PDF OCR и embedded image OCR inside DOCX/PDF не реализованы.

### 8. Requirements / table evidence

Цель: получить deterministic source-backed candidates для requirements и table evidence без генерации и без table analytics.

```powershell
conda run -n etl_env python -m scripts.extract_requirements
conda run -n etl_env python -m scripts.extract_requirements --json-report-path .runtime_eval\requirements_v1.json
conda run -n etl_env python -m scripts.evaluate_tables
conda run -n etl_env python -m scripts.evaluate_tables --json-report-path .runtime_eval\table_evidence_v1.json
```

Эти workflows показывают source-backed candidates, matched terms, categories и previews. Они не являются legal guarantee, SQL/table analytics или automatic calculations.

## Рекомендуемый порядок воспроизведения для сдачи

1. Запустить `conda run -n etl_env python -m pytest -q`.
2. Запустить `conda run -n etl_env python -m scripts.demo_customer_flow`.
3. Проверить один файл через `scripts.inspect_document_structure`.
4. Выполнить chunk export/audit smoke.
5. Запустить OCR smoke, если Tesseract установлен.
6. Запустить external validation bounded mode, если `D:\Projects\etl_service_backup\Example_data` доступен.
7. Удалить/не коммитить runtime artifacts.

Stage 38.6 отдельно закрывает final cleanup & verification checklist. Этот документ только упаковывает experiments/evaluation workflows.
Финальный verification/cleanup checklist находится в `docs/project/FINAL_DELIVERY_CHECKLIST.md`.

## Где появляются результаты

Результаты experiments должны появляться только в:

- `.runtime_eval\...`;
- explicit user-provided temporary paths.

Generated reports, temporary workspaces и runtime outputs не коммитятся. Evaluation scratch не должен писаться в production `storage/index`, `storage/results` или `storage/uploads`.

## Dataset policy

- `first_test_data` - локальные sample files в repository.
- External `D:\Projects\etl_service_backup\Example_data` - path-only evidence dataset, не коммитится и не копируется в repository.
- QA file: `D:\Projects\etl_service_backup\Example_data\[ОТВЕТЫ] Данные для тестирования\test_with_answers.csv`.
- QA file является TSV despite `.csv` extension.
- Training data в repository не коммитится.

## Как добавить будущий experiment

1. Добавить script или documented command.
2. Направить output только в `.runtime_eval` или explicit temporary path.
3. Описать expected metrics.
4. Добавить cleanup note.
5. Не менять production behavior без отдельного stage.
6. Не добавлять external data, generated reports или notebooks только ради видимости.

## Known limitations

- Experiments не доказывают full RAG.
- Нет semantic retrieval или vector DB.
- Нет LLM generation.
- Нет scanned PDF OCR.
- Нет embedded image OCR.
- Нет table analytics.

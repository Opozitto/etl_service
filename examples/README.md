# Примеры

Короткие команды для локальной проверки ETL Service. Подробная установка и workflow описаны в [docs/setup.md](../docs/setup.md).

## Sample corpus

```powershell
python -m scripts.batch_process --input-dir first_test_data
python -m scripts.rebuild_corpus
```

## Search

```powershell
python -m scripts.demo_search --query "экология проект"
```

## Demo flow

```powershell
python -m scripts.demo_customer_flow
```

## Один файл

```powershell
python -m scripts.inspect_document_structure --input-path "D:\path\file.docx"
```

Generated output остается локальным и не коммитится.

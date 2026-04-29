# CUSTOMER SCENARIOS

## Stage 10 goal

Зафиксировать customer scenarios and evaluation set для пилотного трека до того, как Stage 11–17 начнут уточнять ask / OCR / tables / summarization / integration. Это docs-level baseline, который связывает текущий local ETL/search/evaluation foundation с реальными задачами экологов-проектировщиков.

## Primary user

Основной пользователь: эколог-проектировщик.

Он работает с исходными файлами клиента, нормативной базой, проектной документацией, шаблонами и методическими материалами. Для него критичны source-backed поиск, extractive QA, извлечение требований и данных для расчётов, а также контроль качества корпуса.

## MVP / pilot scenarios

### S1. Source-backed search

Пользователь ищет фрагменты или разделы в документах клиента или нормативной базе.

Expected output:

- список найденных documents / chunks;
- `file` / `document_id`;
- `section_title`;
- `snippet`;
- `score` / `rank`.

### S2. Source-backed extractive QA

Пользователь задаёт вопрос по загруженным документам.

Expected output:

- короткий ответ строго по найденным источникам;
- ссылки на `file` / `document_id` / `chunk` / `section`;
- если данных нет, явное `нет информации в корпусе`.

### S3. Requirements extraction

Пользователь просит найти требования или нормативные условия.

Expected output:

- найденные требования как extractive snippets;
- source references;
- без генерации новых требований.

### S4. Calculation inputs discovery

Пользователь ищет данные для расчётов или обоснований.

Expected output:

- найденные численные и текстовые фрагменты;
- source references;
- пометка, если требуются таблицы или OCR.

### S5. Document quality / audit

Пользователь или разработчик проверяет пригодность корпуса.

Expected output:

- batch report;
- corpus audit;
- retrieval eval;
- problem documents.

### S6. OCR / image intake candidate

Скан или фото документа.

Expected output на текущем этапе:

- limitation / future OCR spike;
- не обещать готовый OCR.

### S7. Summarization / draft generation candidate

Пользователь просит саммари или черновик раздела.

Expected output на текущем этапе:

- future spike;
- не обещать LLM generation как готовое.

## Out of scope for Stage 10

Пока вне scope:

- production OCR;
- semantic retrieval;
- vector DB;
- полноценный RAG;
- LLM generation / answer synthesis;
- автоматическая генерация фрагментов документации;
- обещание поддержки HEIC как готового intake-пути;
- обещание XLS/XLSX table intelligence beyond current baseline;
- внешние proprietary API.

## Expected outputs

Stage 10 должен зафиксировать не функциональную реализацию, а контракт пилотного трека:

- пользовательские сценарии;
- expected outputs для поиска, QA, extraction и audit;
- ограничения текущего baseline;
- минимальный evaluation set;
- связь с будущими этапами.

## Acceptance criteria

- Сценарии сформулированы для эколога-проектировщика, а не абстрактного пользователя.
- Каждый MVP/pilot scenario имеет ожидаемый результат, привязанный к source-backed поведению.
- Ничего из OCR / RAG / LLM generation не объявлено готовым, если это не подтверждено кодом.
- Минимальный evaluation set покрывает supported now / partial / future границы.
- Материал связывает текущий baseline Stage 7–9 с Stage 11–17.

## Minimal evaluation set

Ниже минимальный набор evaluation cases для Stage 10. Он фиксирует, какие вопросы должны проходить через current foundation, а какие должны быть честно ограничены.

| id | scenario | user_question_or_task | input_scope | expected_behavior | expected_sources_required | current_stage_support | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EC-01 | Source-backed search | Найти `экология проект` в корпусе | Local corpus index and saved JSON results | Вернуть top hits с `file`, `document_id`, `section_title`, `snippet`, `score` / `rank` | yes | supported now | Базовая проверка retrieval proof |
| EC-02 | Requirements search | Найти требования по ПДВ / выбросам | Documents from client corpus and normative source files | Показать extractive snippets с source references | yes | supported now | Требования должны быть извлечены, а не сгенерированы |
| EC-03 | Extractive QA | Какой срок или условие указан в документе? | Chunk-level corpus content | Короткий ответ строго по источникам | yes | supported now | Если ответа нет, вернуть `нет информации в корпусе` |
| EC-04 | No-answer case | Есть ли в корпусе сведения о X, если их нет? | Relevant corpus subset | Явно сообщить, что информации нет | yes | supported now | Проверка честного отказа без галлюцинации |
| EC-05 | Calculation inputs | Найти исходные данные для расчёта | Text and numeric fragments in docs | Вернуть числа и фрагменты с references | yes | partial | Может требоваться table awareness и/или OCR |
| EC-06 | Audit visibility | Документ без chunks должен быть замечен audit'ом | Batch corpus outputs and audit report | Появление в problem documents / audit summary | no | supported now | Связка с Stage 7–9 audit foundation |
| EC-07 | OCR limitation | Скан или фото документа | JPG / JPEG / PNG / HEIC candidate inputs | Отметить limitation / future OCR spike | no | future | Пока не обещать готовый OCR |
| EC-08 | Table input | XLS / XLSX table-heavy document | Spreadsheet or table-like source | XLS and XLSX baseline support with flattened lexical retrieval | yes | supported now | Table extraction works for XLS and XLSX, but this is flattened lexical retrieval, not full table-aware reasoning |
| EC-09 | Summarization | Сделать краткое саммари документа | Source document plus request for summary | Future spike only | yes | future | Не объявлять готовую summarization |
| EC-10 | Draft generation | Подготовить черновик раздела документации | Project doc context and task brief | Future spike only | yes | future | Не объявлять готовую LLM generation |
| EC-11 | Source attribution | Указать, откуда взят ответ | Search hits and chunk references | Answer must carry explicit source references | yes | supported now | Это критерий доверия для pilot track |
| EC-12 | Problem documents | Найти проблемные документы корпуса | Index, manifest, batch and audit reports | Audit should surface duplicates, warnings, missing chunks, and low-quality items | no | supported now | Использует Stage 7–9 reporting layer |

## Connection to Stage 11–17

- Stage 11 should prove ask / extractive QA with sources on top of the current corpus, without turning it into generation.
- Stage 12 should test OCR / image intake and separate confirmed support from limitation, especially for scans and phone photos.
- Stage 13 keeps the historical XLS / tables decision in the record; Stage 14 supersedes the old unsupported-XLS state with practical baseline support.
- Stage 15 should align customer demo readiness, ingestion-search QA, supported formats, and scenario matrices after XLS support.
- Stage 16 should evaluate summarization / draft generation as a future spike, not as a baseline claim.
- Stage 17 should connect the confirmed pieces into a prototype integration flow, while keeping audit and eval visible.

## Notes on the current baseline

- Stage 7–9 already provide batch reporting, corpus audit, and retrieval quality evaluation.
- That makes source-backed search and source-backed proof the right immediate pilot direction.
- OCR, semantic retrieval, vector DB, RAG, and LLM generation remain outside the confirmed baseline.

## Stage 14 note

- EC-08 now reflects practical `.xls`/`.xlsx` table baseline support.
- The scenario set still uses flattened lexical retrieval and does not claim full table reasoning.
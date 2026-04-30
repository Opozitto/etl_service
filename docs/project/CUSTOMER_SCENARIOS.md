# CUSTOMER SCENARIOS

## Цель Stage 10

Зафиксировать customer scenarios and evaluation set для пилотного трека до того, как Stage 11–17 начнут уточнять ask / OCR / tables / summarization / integration. Это docs-level baseline, который связывает текущий local ETL/search/evaluation foundation с реальными задачами экологов-проектировщиков.

## Основной пользователь

Основной пользователь: эколог-проектировщик.

Он работает с исходными файлами клиента, нормативной базой, проектной документацией, шаблонами и методическими материалами. Для него критичны source-backed поиск, extractive QA, извлечение требований и данных для расчётов, а также контроль качества корпуса.

## MVP / pilot-сценарии

### S1. Source-backed search

Пользователь ищет фрагменты или разделы в документах клиента или нормативной базе.

Ожидаемый результат:

- список найденных documents / chunks;
- `file` / `document_id`;
- `section_title`;
- `snippet`;
- `score` / `rank`.

### S2. Source-backed extractive QA

Пользователь задаёт вопрос по загруженным документам.

Ожидаемый результат:

- короткий ответ строго по найденным источникам;
- ссылки на `file` / `document_id` / `chunk` / `section`;
- если данных нет, явное `нет информации в корпусе`.

### S3. Requirements extraction

Пользователь просит найти требования или нормативные условия.

Ожидаемый результат:

- найденные требования как extractive snippets;
- source references;
- без генерации новых требований.

### S4. Calculation inputs discovery

Пользователь ищет данные для расчётов или обоснований.

Ожидаемый результат:

- найденные численные и текстовые фрагменты;
- source references;
- пометка, если требуются таблицы или OCR.

### S5. Document quality / audit

Пользователь или разработчик проверяет пригодность корпуса.

Ожидаемый результат:

- batch report;
- corpus audit;
- retrieval eval;
- problem documents.

### S6. OCR / image intake candidate

Скан или фото документа.

Ожидаемый результат на текущем этапе:

- limitation / future OCR spike;
- не обещать готовый OCR.

### S7. Summarization / draft generation candidate

Пользователь просит саммари или черновик раздела.

Expected output на текущем этапе:

- future spike;
- не обещать LLM generation как готовое.

## Вне scope Stage 10

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

## Ожидаемые результаты

Stage 10 должен зафиксировать не функциональную реализацию, а контракт пилотного трека:

- пользовательские сценарии;
- expected outputs для поиска, QA, extraction и audit;
- ограничения текущего baseline;
- минимальный evaluation set;
- связь с будущими этапами.

## Критерии приёмки

- Сценарии сформулированы для эколога-проектировщика, а не абстрактного пользователя.
- Каждый MVP/pilot scenario имеет ожидаемый результат, привязанный к source-backed поведению.
- Ничего из OCR / RAG / LLM generation не объявлено готовым, если это не подтверждено кодом.
- Минимальный evaluation set покрывает supported now / partial / future границы.
- Материал связывает текущий baseline Stage 7–9 с Stage 11–17.

## Минимальный evaluation set

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
| EC-08 | Table input | XLS / XLSX table-heavy document | Spreadsheet or table-like source | XLS и XLSX поддерживаются на baseline-уровне с flattened lexical retrieval | yes | supported now | Table extraction работает для XLS и XLSX, а row-level chunks добавляют sheet/table/row/column-value context; это всё ещё flattened lexical retrieval, а не полноценная table-aware analytics |
| EC-09 | Summarization | Сделать краткое саммари документа | Source document plus request for summary | Future spike only | yes | future | Не объявлять готовую summarization |
| EC-10 | Draft generation | Подготовить черновик раздела документации | Project doc context and task brief | Future spike only | yes | future | Не объявлять готовую LLM generation |
| EC-11 | Source attribution | Указать, откуда взят ответ | Search hits and chunk references | Answer must carry explicit source references | yes | supported now | Это критерий доверия для pilot track |
| EC-12 | Problem documents | Найти проблемные документы корпуса | Index, manifest, batch and audit reports | Audit should surface duplicates, warnings, missing chunks, and low-quality items | no | supported now | Использует Stage 7–9 reporting layer |

## Связь со Stage 11–17

- Stage 11 должен доказать ask / extractive QA с источниками поверх текущего корпуса, без превращения этого в generation.
- Stage 12 должен протестировать OCR / image intake и отделить подтверждённую поддержку от ограничений, особенно для сканов и фото с телефона.
- Stage 13 сохраняет историческое решение по XLS / tables; Stage 14 superseded старое состояние unsupported-XLS практической baseline-поддержкой.
- Stage 15 должен выровнять customer demo readiness, ingestion-search QA, поддерживаемые форматы и scenario matrix после поддержки XLS.
- Stage 16 должен оценивать summarization / draft generation как будущий spike, а не как baseline claim.
- Stage 17 должен связать подтверждённые части в prototype integration flow, сохраняя видимыми audit и eval.
- Stage 17 demo helper может читать текущий snapshot корпуса, пересобирать индекс только по явному флагу и честно показывать текущий baseline.

## Примечания к текущему baseline

- Stage 7–9 уже дают batch reporting, corpus audit и retrieval quality evaluation.
- Это делает source-backed search и source-backed proof правильным ближайшим пилотным направлением.
- OCR, semantic retrieval, vector DB, RAG и LLM generation остаются вне подтверждённого baseline.

## Примечание Stage 14

- EC-08 теперь отражает практическую поддержку `.xls` / `.xlsx` на baseline-уровне.
  - Набор сценариев по-прежнему использует flattened lexical retrieval и не заявляет полноценное table reasoning.
  - Row-level spreadsheet chunks улучшают source-backed table row/value retrieval без table-aware analytics.

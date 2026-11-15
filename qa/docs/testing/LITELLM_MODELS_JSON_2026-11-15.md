# Модели LiteLLM: JSON и JSON Schema (15.11.2026)

Проверен шлюз `https://litellmru.ds-hub-cf.ru/v1` по ключу из `services/school_events_llm/.env`.
Ключ в отчёт не попадает.

## Доступные модели

`GET /v1/models` вернул 7 записей:

| Модель | Тип |
|---|---|
| `GigaChat-2-Max` | chat |
| `GigaChat-2-Pro` | chat |
| `GigaChat-3-Pro` | chat |
| `GigaChat-3-Lightning` | chat |
| `GigaChat-2` | chat |
| `Qwen3.8-27B` | chat |
| `frida-decisions` | evaluation, не chat |
| `EmbeddingsGigaR` | embeddings |

## Как проверял

Два этапа.

**Базовый:** по одному запросу на режим — `json_object`, `json_schema` со `strict:true` и `strict:false`, плюс простая и сложная схема.

**Строгий:** для каждой chat-модели несколько повторов:

- `json_object` — 3 раза;
- простая схема `{name, age, skills[], minItems: 2}` — 3 раза со `strict:true` и 1 раз со `strict:false`;
- «провокационная» схема `{answer: enum ["SCHEMA"]}`, `additionalProperties:false`, а в промпте просят `answer="PROMPT"` и лишнее поле — 2 раза;
- большая схема: 8 этапов, по 3 действия учителя и ученика, 5 целей, 3 риска — 2 раза, `max_tokens=8000`.

Ответ считался успешным только если JSON парсится и проходит рекурсивную проверку: типы, `required`, `enum`, `minItems`, `additionalProperties`.

## Строгий результат

| Модель | `json_object` | Простая схема, strict | Простая, loose | Провокационная | Большая схема |
|---|---|---|---|---|---|
| `GigaChat-2-Max` | **0/3, 400** | **0/3** | **0/1** | 2/2 | **0/2** |
| `GigaChat-2-Pro` | **0/3, 400** | 3/3 | 1/1 | 2/2 | 2/2 |
| `GigaChat-3-Pro` | **0/3, 400** | 3/3 | 1/1 | 2/2 | 2/2 |
| `GigaChat-3-Lightning` | **0/3, 400** | 3/3 | 1/1 | 2/2 | **0/2** |
| `GigaChat-2` | **0/3, 400** | 3/3 | 1/1 | 2/2 | **0/2** |
| `Qwen3.8-27B` | **3/3** | 3/3 | 1/1 | 2/2 | **1/2** |

## Что именно сломалось

- **`GigaChat-2-Max`** на простой схеме три раза вернул `skills: ["Python"]` вместо двух навыков. `minItems: 2` не соблюдён, хотя HTTP 200. На большой схеме вернул 1 цель вместо 5.
- **`GigaChat-3-Lightning` и `GigaChat-2`** на большой схеме вернули 6 этапов вместо 8 (`minItems: 8` не соблюдён).
- **`Qwen3.8-27B`** на большой схеме: один запрос завершился `ReadTimeout` при таймауте 300 с, второй прошёл. То есть даже с 8000 токенов большой ответ не гарантирован по времени.
- **`GigaChat-2-Pro` и `GigaChat-3-Pro`** прошли все проверки в этом наборе.
- **`json_object`** у всех GigaChat — 400: `GigaChat does not support response_format.type='json_object'. Use response_format.type='json_schema' with a schema.`

## Ответ на вопрос «100%?»

**Нет, 100% гарантии нет.** Схема принимается, но провайдер не всегда жёстко соблюдает ограничения:

- `minItems` может быть нарушен;
- большой ответ может обрезаться или не уложиться в таймаут;
- `strict:true` не гарантирует соблюдение всех ключевых слов схемы.

Это не теория: на `GigaChat-2-Max`, `GigaChat-3-Lightning`, `GigaChat-2` и `Qwen` получены реальные несоответствия.

## Практический вывод

- **GigaChat:** только `json_schema`, `json_object` нельзя.
- **Qwen:** можно и `json_object`, и `json_schema`.
- Для большого JSON: `max_tokens` с запасом, проверка `finish_reason`, валидация по схеме и retry.
- `strict:true` оставлять, но не полагаться на него как на гарантию.
- **Всегда** валидировать ответ на своей стороне. Тогда при несоответствии можно повторить запрос.

## Ограничения

- По 1–3 повтора на сценарий; это не статистика на сотнях запусков.
- Проверены две схемы и одна большая; `$ref`, рекурсивные схемы и tool calling не проверялись.
- `frida-decisions` и `EmbeddingsGigaR` в chat-тестах не участвуют.

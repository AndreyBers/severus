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

Для каждой chat-модели — 4 запроса через `POST /v1/chat/completions`:

1. обычный текстовый ответ — проверка доступности;
2. `response_format={"type":"json_object"}` + просьба вернуть JSON;
3. `response_format={"type":"json_schema","json_schema":{"name":"person","strict":true,"schema":...}}`;
4. тот же schema, но `strict:false`.

Схема: объект `{name: string, age: integer, skills: string[]}`, `additionalProperties: false`.
Ответ проверялся вручную: JSON парсится, нужные ключи есть, типы совпадают, лишних ключей нет.

Дополнительно — сложная схема: `title`, `level` (enum), `items[]` из `{name, done}`.

## Результаты

| Модель | Chat | `json_object` | `json_schema` | Сложная схема |
|---|---|---|---|---|
| `GigaChat-2-Max` | да | **нет, 400** | да | да |
| `GigaChat-2-Pro` | да | **нет, 400** | да | да |
| `GigaChat-3-Pro` | да | **нет, 400** | да | да |
| `GigaChat-3-Lightning` | да | **нет, 400** | да | да |
| `GigaChat-2` | да | **нет, 400** | да | да |
| `Qwen3.8-27B` | да | да | да | да, но нужен больший `max_tokens` |
| `frida-decisions` | нет | нет | нет | не chat-модель |
| `EmbeddingsGigaR` | — | — | — | embeddings, не проверялась |

### GigaChat

Все пять GigaChat-моделей **не принимают `json_object`**:

```
GigaChat does not support response_format.type='json_object'.
Use response_format.type='json_schema' with a schema.
```

Но **`json_schema` работает** и со `strict:true`, и со `strict:false`: ответ валидный, ключи и типы соответствуют схеме. Сложная схема с enum и массивом объектов тоже прошла на всех пяти моделях.

### Qwen3.8-27B

Принимает и `json_object`, и `json_schema` (strict true/false). На сложной схеме с `max_tokens=300` ответ обрезался: reasoning занял весь бюджет. С `max_tokens=2500` вернулся валидный JSON по схеме. Для Qwen с рассуждениями нужен запас токенов.

### frida-decisions

На `/chat/completions` возвращает 400:

```
Unmapped LLM provider for this endpoint
```

Это evaluation-модель, её нужно вызывать через decisions-эндпоинт, а не как chat.

## Вывод

- Для **GigaChat** использовать только `response_format.type="json_schema"`. `json_object` гарантированно даёт 400.
- Для **Qwen3.8-27B** можно и `json_object`, и `json_schema`; для сложных схем ставить `max_tokens` не меньше 2000–2500.
- `strict:true` принимается, но клиентскую валидацию JSON всё равно оставить: провайдеры по-разному трактуют strict.
- `frida-decisions` и `EmbeddingsGigaR` в chat-тестах не участвуют.

## Ограничения

- По одному запросу на режим; нагрузка и стабильность не измерялись.
- Проверены две схемы: простая и с enum/массивом; вложенные `$ref` и очень большие схемы не проверялись.
- Tool calling / function calling не проверялся.

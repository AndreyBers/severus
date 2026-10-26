# Северус

ИИ-сервис для подготовки школьных событий. Командный проект по кейсу Сбер + УрФУ «Школьные события».

## Структура репозитория

| Путь | Что это | Описание |
|---|---|---|
| `frontend/` | веб-интерфейс (React + TypeScript + Vite) | `frontend/README.md` |
| `backend/` | общий бэкенд: публичный API для фронтенда, порт 8000 | `docs/FRONTEND_API.md` |
| `services/school_events_llm/` | LLM-сервис генерации сценариев | `services/school_events_llm/README.md` |
| `catalog/` | единый каталог событий и источников | `catalog/README.md` |
| `acceptance/` | таблицы аудита источников и возрастной проверки каталога | - |
| `tests/` | тесты бэкенда | - |

## Как части связаны

```
frontend :5173  ->  backend :8000  ->  services/school_events_llm  ->  LLM
                         \                      /
                          '----- catalog/ -----'
```

Фронтенд работает только с бэкендом. Бэкенд проверяет запрос и поддерживает два режима генерации: встроенный `mock` и внутренний HTTP-вызов `school_events_llm`. Каталог событий один на всех: бэкенд отдаёт из него список событий, а LLM-сервис использует те же карточки при сборке промптов.

## Быстрый старт бэкенда

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Swagger: `http://127.0.0.1:8000/docs`.

## Запуск LLM-сервиса

Из каталога `services/school_events_llm/`:

```bash
python -m app serve
```

Для подключения основного Backend задайте `GENERATOR_MODE=llm_service`. Подробности и переменные окружения описаны в `docs/LLM_INTEGRATION.md`.

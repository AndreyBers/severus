# Северус — Backend API для Frontend

## Статус

Sprint 1. Рабочий mock-Backend без подключения LLM.

Base URL при локальном запуске:
http://127.0.0.1:8000

Swagger:
http://127.0.0.1:8000/docs

## Запуск

1. Создать и активировать Python virtual environment.
2. Установить зависимости: pip install -r requirements.txt
3. Запустить сервер:

python -m uvicorn backend.main:app --reload --port 8000

## Доступные маршруты

GET /api/v1/health
Проверка работоспособности.

GET /api/v1/catalog/events
Каталог доступных мероприятий.

GET /api/v1/catalog/options
Параметры конструктора и допустимые значения.

POST /api/v1/generations
Создание задания на генерацию. Ответ HTTP 202.

GET /api/v1/generations/{job_id}
Получение текущего статуса задания.

GET /api/v1/projects/{project_id}
Получение завершённого проекта со сценариями.

## Пример POST-запроса

{
  "event_id": "knowledge_day",
  "region_id": "RU-SVE",
  "grade": 6,
  "pupils_count": 25,
  "duration_minutes": 45,
  "format": "class_hour",
  "generation": {
    "variants_count": 2,
    "language": "ru"
  }
}

## Алгоритм Frontend

1. Получить события и параметры конструктора.
2. Отправить POST /api/v1/generations.
3. Сохранить job_id, project_id, status_url, project_url.
4. Опросить status_url до completed или failed.
5. При completed запросить project_url.
6. Отобразить variants[].concept, roles, timeline, materials.
7. Показывать предупреждения из quality_report.

## Формат ошибок

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Некорректные параметры запроса",
    "field": null,
    "retryable": false
  }
}

## Ограничения Sprint 1

- Генерация тестовая, настоящая LLM не подключена.
- Результаты хранятся в памяти одного процесса.
- После перезапуска сервера задания исчезают.
- Использовать один процесс Backend без нескольких workers.
- Полное соответствие контракту v1.4 ещё не подтверждено.
- GET отдельного варианта и повторная генерация отсутствуют.
- Авторизация пользователей пока не реализована.
- Локальный адрес 127.0.0.1 недоступен с другого компьютера.
- CORS разрешает локальные Frontend-адреса 5173 и 3000.

# Перепрогон после main + PR #30 (15.11.2026)

## 1. Сборка

- `QA/Maksim`, merge `82f7992`.
- `origin/main` `00bd66b`: backend LLM failures, каталог 1114 (christmas, last_bell, unity_day).
- PR #30 `036f713`: INNER-TIMING, TECH-ID, 90% script threshold, параллельные варианты, block timing hints.
- PR #27/#28/#29 не влиты.

## 2. Результаты

| Проверка | Результат |
|---|---|
| Юнит-тесты LLM-сервиса | 364 passed, 1159 subtests |
| QA-тесты | 30 passed |
| Backend | 65 passed |
| `qa_check_1114c` | 10/10 `completed`, критичных — 0 |
| API-регрессия | 7/7 `completed` |
| UI-регрессия | 17/17 PASS |

## 3. Reasoning medium

- Проверка с `LLM_REASONING=*=medium`.
- В манифестах `reasoning_effort=medium`, `response.reasoning.txt` создаётся.
- 3 варианта: `job_393071c8699c45acb33d78ece1449057`, 158,8 с, 3/3 — параллельный запуск работает.
- В `config/generation.json` по умолчанию `null`; medium включается через env/`.env`.

## 4. Предупреждения

| Прогон | Предупреждения |
|---|---|
| `c01` defender 8/45 | `INNER-TIMING` (block_01 — ложный: параллельное обсуждение 5 групп) |
| `c02` womens 3/30 parents vote | — |
| `c03` victory 9/45 no tech | — |
| `c04` teachers 11/30 | — |
| `c05` last_bell 4/45 parents award | — |
| `c06` graduation 11/60 jury | — |
| `c07` labour 7/45 no groups | — |
| `c08` middle urals 5/30 | — |
| `c09` new_year 2/30 helpers 2var | `INNER-TIMING` (v2 block_04 — ложный: параллельное обсуждение) |
| `c10` sverdlovsk 9/45 large class | — |
| API `minimal_resources` | `TECH-ID-IN-TEXT` на `tissues`, `water cups` |
| UI | — |

## 5. Закрыто

- **BUG-05** — 90% порог, `SCRIPT-SHORT` больше не шумит.
- **BUG-11** — 2023/1699 без ложных предупреждений.
- **BUG-16** — внутренние ID в репликах не воспроизводятся; UI чист.
- **BUG-18** — станции считаются верно.
- **BUG-19** — вертеп убран.
- **BUG-21** — large_class_35 прошёл, schema-fail не повторился.
- **BUG-22** — 3 варианта 158,8 с, параллельно.
- **BUG-14 / BUG-17 / BUG-09** — подтверждены.

## 6. Остаётся

- **BUG-20 (P2):** `INNER-TIMING` считает параллельное обсуждение групп последовательными выступлениями: `c01` block_01 и `c09` v2 block_04 — 5 групп × 2 мин = 10 при блоке 5. Файл `app/validation/inner_timing.py:43`, `:192`, `:206-215`.
- **BUG-23 (P3):** `TECH-ID-IN-TEXT` ловит обычные английские слова `tissues`, `water cups` в `materials.art_supplies` (`job_b56da75d30c44767b5823d50f90f81b1`).
- **BUG-12 / BUG-15 (P2):** фронтенд: нет `parent_audience_engagement`, по умолчанию `detailed`.
- **BUG-06 (P2):** формат issue не по ТЗ.
- **BUG-04 / BUG-07 (P3):** fixture и демо-каталог.
- **BUG-13** — отложен до PR #27.

P1 нет.

## 7. Время и токены

| Группа | Запросов | Время | Токены |
|---|---:|---:|---:|
| `qa_check_1114c` | 10 | 26,4 мин | 324 764 |
| API-регрессия | 7 | 16,8 мин | 254 175 |
| UI | 2 | 4,7 мин | 77 987 |
| **Итого** | **19** | **47,9 мин** | **656 926** |

Prompt — 476 148, completion — 180 778; среднее — 34 575 токенов на запрос. Wall-clock около 47 минут.

## 8. Вывод

Основные исправления подтверждены: 90% порог, TECH-ID, 1612/станции/вертеп, жюри, родители, 35 учеников и 3 варианта. Блокирующих P1 нет. Остались ложный `INNER-TIMING` на параллельных обсуждениях и P3-калибровка TECH-ID; фронтенд и формат issue — без изменений.

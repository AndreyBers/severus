**Андрею: итог после main + PR #30 (15.11.2026)**

Сборка: QA/Maksim, merge 82f7992: origin/main 00bd66b + PR #30 036f713 (INNER-TIMING, TECH-ID, 90% script threshold, параллельные варианты).

**Reasoning medium**

- Проверял с `LLM_REASONING=*=medium`; в манифестах всех этапов `reasoning_effort=medium`, `response.reasoning.txt` создаётся.
- В `config/generation.json` по умолчанию `null`; medium включается через env/`.env`.
- 3 варианта теперь идут параллельно: 158,8 с вместо 17 минут.

**Что закрыто и подтверждено**

| Баг | Что проверял | Результат |
|---|---|---|
| **BUG-05** | порог 90% | `qa_check_1114c`, `variants_2` — без `SCRIPT-SHORT` |
| **BUG-11** | 2023/1699 | без ложных `FACT-UNREGISTERED` |
| **BUG-16** | технические ID | UI `job_60e644176eea409e9a6f6c4bf18a6f6c` чист, `commitments_book_pages` не воспроизвёлся |
| **BUG-18** | станции | 5×4 в 20 — без предупреждения |
| **BUG-19** | вертеп | убран |
| **BUG-21** | 35 учеников | `job_3157f478f4074a02875b1f624b0b4f2f` — `completed`, schema-fail не повторился |
| **BUG-22** | 3 варианта | `job_393071c8699c45acb33d78ece1449057` — 158,8 с, 3/3 |
| **BUG-14 / BUG-17 / BUG-09** | жюри, родители, памятка | подтверждены |

**Что осталось**

| Баг | Что это за баг | Где именно | Трасса |
|---|---|---|---|
| **BUG-20** (P2) | `INNER-TIMING` складывает параллельное обсуждение групп как последовательные выступления. | `app/validation/inner_timing.py:43` (`_UNIT_PAIR`), `:192` (ветка пар), `:206-215` (интервал/презентации) | `job_20261115_123555_b0c44a`: c01 block_01, 5 групп × 2 мин = 10 при блоке 5; `job_20261115_125732_3adb26`: c09 v2 block_04, 5 групп × 2 = 10 при блоке 5 |
| **BUG-23** (P3) | `TECH-ID-IN-TEXT` ловит обычные английские слова, а не ID. | `app/validation/checks.py:442`, `humanize.leftover_ids` | `job_b56da75d30c44767b5823d50f90f81b1`: `tissues`, `water cups` в `materials.art_supplies` |
| **BUG-06** (P2) | Формат issue не по ТЗ 16.2. | `quality_report.issues`: нет `issue_id/category/repairable/suggested_action` | — |
| **BUG-04** (P3) | Fixture выбирает эталон по порядку, а не по `event_id`. | `app/llm/fixture.py:41-51` | — |

**Время и токены**

| Группа | Запросов | Время | Токены |
|---|---:|---:|---:|
| `qa_check_1114c` | 10 | 26,4 мин | 324 764 |
| API-регрессия | 7 | 16,8 мин | 254 175 |
| UI | 2 | 4,7 мин | 77 987 |
| **Итого** | **19** | **47,9 мин** | **656 926** |

Prompt — 476 148, completion — 180 778; среднее — 34 575 токенов на запрос. Wall-clock около 47 минут.

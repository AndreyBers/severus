"""Технические ID в промптах (прогон 15.11, разбор сырых ответов GigaChat по всем трассам).

Модель пишет ID в тексте там, где видит их в промпте рядом со своим заданием:
- этап блоков: 10 из 13 случаев на 461 ответ - ID материала из строки своего блока
  («материалы: recipe_cards ← ТЕКУЩИЙ БЛОК» -> «(раздаёт `recipe_cards`)»);
- этап материалов: 17 из 89 ответов - ID в памятке педагогу в скобках после названия
  («Распечатайте листы планирования (worksheet_individual_plans)»), как в формате списка материалов.
Поэтому этап блоков ID материалов не видит вовсе (материалы блока программа берёт из плана), а этап
материалов видит их один раз - в списке для поля `material_id`, после названия.
"""

import json
import tempfile
import unittest
from pathlib import Path

from app.generation.humanize import humanize_variant
from app.generation.pipeline import Generator
from app.llm.fixture import FixtureLLM
from app.trace import RunTrace
from tests.helpers import catalog, golden, request, settings

PLAN = {
    "variant_id": "v2", "title": "Новогодний семейный маршрут",
    "concept": {"summary": "Станции семейного маршрута", "goal": "Праздничная атмосфера",
                "values_to_mechanics": [{"value_id": "family", "mechanic_type": "discussion", "mechanic": "Обсуждение традиций",
                                         "block_ids": ["block_02"]}]},
    "grouping_request": {"block_ids": ["block_02", "block_03"]},
    "roles": [{"role_id": "teacher_1", "title": "Ведущий педагог", "participant_type": "teacher", "count": 1}],
    "blocks": [
        {"block_id": "block_01", "title": "Знакомство с маршрутом", "purpose": "Правила", "role_ids": ["teacher_1"],
         "planned_material_ids": ["route_cards"]},
        {"block_id": "block_02", "title": "Станция «Традиции»", "purpose": "Обсуждение", "role_ids": ["teacher_1"],
         "planned_material_ids": ["traditions_cards"]},
        {"block_id": "block_03", "title": "Станция «Семейные рецепты»", "purpose": "Оформление", "role_ids": ["teacher_1"],
         "planned_material_ids": ["recipe_cards", "decoration_kit"]},
    ],
    "planned_materials": [
        {"material_id": "route_cards", "type": "activity_card", "title": "Маршрутные листы", "purpose": "Движение по станциям"},
        {"material_id": "traditions_cards", "type": "worksheet", "title": "«Карточки для обсуждения традиций»", "purpose": "Обмен"},
        {"material_id": "recipe_cards", "type": "props_checklist", "title": "Карты оформления рецептов", "purpose": "Оформление"},
        {"material_id": "decoration_kit", "type": "props_checklist", "purpose": "Украшения"},
    ],
}
GRID = [(0, 3), (3, 7), (10, 5)]
IDS = [m["material_id"] for m in PLAN["planned_materials"]]


class PlanTextTest(unittest.TestCase):
    def test_no_material_ids_in_plan(self):
        """В строках блоков и списке материалов - названия; этапы в делении и ценностях - тоже по названию."""
        text = Generator.plan_text(PLAN, GRID, ("small_groups", [5, 5, 5, 5]), "block_03")
        for material_id in IDS:
            self.assertNotIn(material_id, text)
        self.assertIn("материалы: «Карты оформления рецептов», «Список реквизита»  ← ТЕКУЩИЙ БЛОК", text)
        self.assertIn("этапы: «Станция «Традиции»», «Станция «Семейные рецепты»»", text)
        self.assertIn("Обсуждение традиций - этапы: «Станция «Традиции»»", text)
        self.assertIn("- «Карточки для обсуждения традиций» - рабочий лист - Обмен", text)
        self.assertIn("`block_03`", text)  # по ID блока этап нескольких блоков возвращает ответ

    def test_materials_stage_lists(self):
        """Этапу материалов ID даются один раз, после названия; образец памятки - с названием из плана."""
        listed = Generator.planned_materials_list(PLAN)
        self.assertTrue(listed.startswith("«Маршрутные листы» - `material_id`: `route_cards`, `type`: `activity_card`; "))
        self.assertEqual(Generator.instruction_example(PLAN), "Подготовьте «Маршрутные листы» заранее")
        self.assertEqual(Generator.materials_hint(PLAN, PLAN["blocks"][2]),
                         "; материал называй по названию, например: (раздаёт «Карты оформления рецептов»)")
        blocks = [{"block_id": "block_03", "title": "Рецепты", "start_minute": 10, "duration_minutes": 5, "pupil_actions": ["Рисуют"],
                   "material_ids": ["recipe_cards"], "teacher_script": "Раздаёт карты."}]
        self.assertIn("Материалы: «Карты оформления рецептов»", Generator.blocks_text(blocks, Generator.material_titles(PLAN)))


class ComposedPromptsTest(unittest.TestCase):
    def test_prompts_of_a_run(self):
        """Генерация по эталону: в промптах блоков нет ни одного ID материала плана; в промпте материалов каждый
        ID встречается один раз (список для `material_id`), образец памятки - с названием материала."""
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            trace = RunTrace(run_dir, full_prompts=True, full_responses=False, secrets=[])
            outcome = Generator(settings(), catalog(), FixtureLLM([golden("ex1_knowledge_day")]), trace=trace).run(
                request("ex1_knowledge_day"))
            self.assertEqual(outcome.project["status"], "completed")
            calls = {}
            for call in sorted((run_dir / "calls").iterdir()):
                stage = json.loads((call / "manifest.json").read_text(encoding="utf-8"))["stage"]
                calls.setdefault(stage, []).append(call)
            plan = json.loads((calls["scenario_plan"][0] / "response.parsed.json").read_text(encoding="utf-8"))
            ids = [m["material_id"] for m in plan["planned_materials"]]
            for call in calls["scenario_block"]:
                prompt = (call / "prompt.md").read_text(encoding="utf-8")
                for material_id in ids:
                    self.assertNotIn(material_id, prompt, call.name)
                self.assertIn("например: (раздаёт «", prompt)
            prompt = (calls["materials"][0] / "prompt.md").read_text(encoding="utf-8")
            self.assertEqual({mid: prompt.count(f"`{mid}`") for mid in ids}, {mid: 1 for mid in ids})
            self.assertIn('"teacher_instructions": ["Подготовьте «', prompt)


class FieldNameAsWordTest(unittest.TestCase):
    def test_fact_claims_in_notes(self):
        """Прогон 15.11 после правки промптов: ID материалов в ответах модели - ни одного, но в памятке к материалу
        модель употребила название нашего поля как слово. В тексте - по-русски, без ёлочек."""
        notes = "Разместите на видном месте возле каждой станции. Используйте fact_claims из справки для исторической части."
        variant = {"timeline": [], "roles": [], "teacher_instructions": [],
                   "materials": [{"material_id": "station_tasks", "title": "Задания станций", "content": "", "teacher_notes": notes}]}
        self.assertEqual(humanize_variant(variant), [{"field": "materials.station_tasks.teacher_notes", "ids": ["fact_claims"]}])
        self.assertEqual(variant["materials"][0]["teacher_notes"],
                         "Разместите на видном месте возле каждой станции. Используйте проверенные факты из справки для исторической части.")

    def test_field_name_variants(self):
        """Другой порядок слов, число, опечатка - тоже заменяются; «fact_claim» - точно."""
        cases = {"claims_fact": "проверенные факты", "facts_claims": "проверенные факты", "fact_cliams": "проверенные факты",
                 "fact_claim": "проверенный факт", "fragments_id": "фрагмент источника", "id_source": "источник"}
        for word, expected in cases.items():
            with self.subTest(word=word):
                variant = {"timeline": [], "roles": [], "teacher_instructions": [],
                           "materials": [{"material_id": "station_tasks", "title": "Задания станций", "content": "",
                                          "teacher_notes": f"Используйте {word} из справки."}]}
                humanize_variant(variant)
                self.assertEqual(variant["materials"][0]["teacher_notes"], f"Используйте {expected} из справки.")


if __name__ == "__main__":
    unittest.main()
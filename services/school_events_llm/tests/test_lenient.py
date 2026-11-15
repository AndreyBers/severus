"""Поблажки к форме ответа для GigaChat-3-Pro (`"output_fixes": "lenient"` в профиле), прогон 15.11.

3 Pro писал полный ответ, но ломал форму: опечатки в ключах, раздел не на своём месте, словарь вместо списка,
ключи без кавычек, значение без ключа. 0 генераций из 10. Ответы из трассы - в `fixtures/gigachat3pro`.
Главное условие: у профилей без флага (GigaChat-2-Max) не меняется ничего - это проверяется отдельно
на записанных ответах 2-Max.
"""

import dataclasses
import json
import unittest

from app.contracts.llm import STAGE_MODELS
from app.generation.lenient import fix_output
from app.generation.pipeline import Generator, prepare_stage_output
from app.llm.client import OpenAICompatibleClient
from app.llm.fixture import FixtureLLM
from app.llm.jsonx import extract_json, quote_keys
from tests.helpers import ROOT, catalog, golden, request, settings

FIXTURES = ROOT / "tests" / "fixtures"


def lenient_parse(name: str, plan: dict | None = None):
    """Ответ 3 Pro из трассы через нестрогий разбор и поблажки, как в `call_stage`; результат проверяется схемой."""
    stage = {"scenario_plan": "scenario_plan", "variation_plan": "variation_plan", "scenario_block": "scenario_block",
             "materials": "materials"}[next(s for s in ("scenario_plan", "variation_plan", "scenario_block", "materials") if name.startswith(s))]
    data = extract_json((FIXTURES / "gigachat3pro" / f"{name}.txt").read_text(encoding="utf-8"), lenient=True)
    fixes = fix_output(stage, data, STAGE_MODELS[stage], plan=plan)
    mechanics = {vid: list(v.get("allowed_mechanic_types") or []) for vid, v in catalog().values.items()}
    prepare_stage_output(stage, data, set(), set(catalog().dependencies), mechanics, {})
    return STAGE_MODELS[stage].model_validate(data), fixes


class ProfileFlagTest(unittest.TestCase):
    def test_only_gigachat_3_pro_is_lenient(self):
        models = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))["models"]
        lenient = sorted(key for key, cfg in models.items() if cfg.get("output_fixes") == "lenient")
        self.assertEqual(lenient, ["urfu_gigachat_3_pro"])
        for key, expected in (("urfu_gigachat_2_max", "strict"), ("urfu_gigachat_3_pro", "lenient")):
            cfg = {**models[key], "base_url": "https://gateway.example/v1"}
            self.assertEqual(OpenAICompatibleClient(key, cfg, "k", None).output_fixes, expected)


class GigaChat2MaxUnchangedTest(unittest.TestCase):
    def test_recorded_2_max_answers_parse_the_same(self):
        """Все записанные ответы GigaChat-2-Max в тестах: нестрогий разбор даёт тот же результат, что и обычный
        (в том числе реплики, разбитые на абзацы, и неэкранированные кавычки внутри реплик)."""
        files = sorted(FIXTURES.glob("replay_gigachat_*/*.txt")) + sorted(FIXTURES.glob("bug21_escaped_key_quote/*.txt"))
        self.assertGreater(len(files), 50)
        for path in files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=f"{path.parent.name}/{path.name}"):
                try:
                    strict = extract_json(text)
                except Exception as exc:  # noqa: BLE001 - сравниваем и ошибки
                    strict = type(exc).__name__
                try:
                    lenient = extract_json(text, lenient=True)
                except Exception as exc:  # noqa: BLE001
                    lenient = type(exc).__name__
                self.assertEqual(lenient, strict)

    def test_split_paragraphs_not_orphans(self):
        text = '{"teacher_script": "Абзац один.", "Абзац два.", "pupil_actions": ["Слушают"]}'
        self.assertEqual(quote_keys(text), text)


class QuoteKeysTest(unittest.TestCase):
    def test_cases_from_trace(self):
        self.assertEqual(quote_keys('{\n  "task": "scenario_block",\n  variant_id: "v1",\n  block: {block_id: "block_04", title: "Итог: круг"}\n}'),
                         '{\n  "task": "scenario_block",\n  "variant_id": "v1",\n  "block": {"block_id": "block_04", "title": "Итог: круг"}\n}')
        self.assertEqual(quote_keys('{"order": 3, "планирование и сборка", "activity_type": "team_task"}'),
                         '{"order": 3, "_orphan_1": "планирование и сборка", "activity_type": "team_task"}')
        self.assertEqual(json.loads(quote_keys('{"dependencies": ["paper", printer], "flag": true, "n": null}')),
                         {"dependencies": ["paper", "printer"], "flag": True, "n": None})
        self.assertEqual(json.loads(quote_keys('{"concepts": [{"a": [1], {"b": 2}]}')), {"concepts": [{"a": [1]}, {"b": 2}]})

    def test_valid_json_untouched(self):
        text = '{"a": "x, b: y", "list": [1, {"c": "d, e: f"}], "s": "кавычка \\" и двоеточие: да"}'
        self.assertEqual(quote_keys(text), text)


class TraceAnswersTest(unittest.TestCase):
    def test_answers_pass_schema(self):
        """Ответы 3 Pro, которые не прошли схему в прогоне, после поблажек проходят."""
        expected = {
            "scenario_plan_vtm_top": {"field_moved"},
            "variation_plan_key_activities": {"list_wrapped"},
            "variation_plan_no_title_key": {"value_keyed"},
            "scenario_block_bare_keys": set(),
            "materials_bare_value": set(),
            "materials_typos_audience": {"key_renamed", "enum_fixed"},
            "scenario_plan_typo_minutes": {"field_moved"},
        }
        for name, kinds in expected.items():
            with self.subTest(name=name):
                _, fixes = lenient_parse(name)
                self.assertTrue(kinds <= {f["kind"] for f in fixes}, fixes)

    def test_moved_section_content_kept(self):
        model, fixes = lenient_parse("scenario_plan_vtm_top")
        self.assertEqual([v.value_id for v in model.concept.values_to_mechanics], ["family", "labour_creation"])
        self.assertIn({"kind": "field_moved", "path": "concept", "field": "values_to_mechanics"}, fixes)

    def test_typo_keys(self):
        data = {"concepts": [{"variant_id": "v1", "title": "Т", "summary": "С", "narrative_approch": "Сюжет",
                              "primary_mechanic": "team_game", "engagement_mode": "small_groups",
                              "planned_structure": [{"order": 1, "title": "А", "activity_type": "game", "approx_minutes": 5},
                                                    {"order": 2, "title": "Б", "activity_type": "reflection", "approx_minutes": 5}],
                              "key_activities": [{"activity_type": "game", "description": "Игра"}], "distinctive_result": "Р",
                              "values_to_mechanики": [{"value_id": "family", "mechanic_type": "discussion", "mechanник": "Разговор"}]}]}
        fixes = fix_output("variation_plan", data, STAGE_MODELS["variation_plan"])
        STAGE_MODELS["variation_plan"].model_validate(data)
        self.assertEqual(sorted(f["from"] for f in fixes if f["kind"] == "key_renamed"),
                         ["mechanник", "narrative_approch", "values_to_mechanики"])

    def test_filled_from_plan(self):
        plan = {"blocks": [{"block_id": "block_02", "role_ids": ["teacher_1", "pupils_all"], "planned_material_ids": ["cards"]}]}
        block = {"variant_id": "v1", "block": {"block_id": "block_02", "start_minute": 5, "duration_minutes": 10, "title": "Т",
                                               "purpose": "Ц", "teacher_script": "Реплика педагога достаточной длины.",
                                               "pupil_actions": ["Работают"]}}
        fix_output("scenario_block", block, STAGE_MODELS["scenario_block"], plan=plan)
        self.assertEqual(block["block"]["role_ids"], ["teacher_1", "pupils_all"])
        materials = {"variant_id": "v1", "teacher_instructions": ["Подготовьте"],
                     "materials": [{"material_id": "cards", "type": "activity_card", "title": "Карточки", "audience": "pupils_group",
                                    "content": "Текст карточки достаточной длины.", "teacher_notes": "", "print_required": False,
                                    "estimated_preparation_minutes": 5}]}
        fix_output("materials", materials, STAGE_MODELS["materials"], plan=plan)
        self.assertEqual(materials["materials"][0]["used_in_blocks"], ["block_02"])


class SecondRunTest(unittest.TestCase):
    """Второй прогон 3 Pro 15.11 (19 вариантов из 25): что ещё теряло варианты."""

    def test_print_required_from_dependencies(self):
        data = {"variant_id": "v1", "teacher_instructions": ["Подготовьте"], "materials": [
            {"material_id": "cards", "type": "activity_card", "title": "Карточки", "used_in_blocks": ["block_02"], "audience": "pupils_group",
             "content": "Текст карточки достаточной длины.", "teacher_notes": "", "dependencies": ["printer", "paper"],
             "estimated_preparation_minutes": 5},
            {"material_id": "markers", "type": "props_checklist", "title": "Маркеры", "used_in_blocks": ["block_02"], "audience": "teacher",
             "content": "Маркеры для доски, по одному на группу.", "teacher_notes": "", "dependencies": ["markers"],
             "estimated_preparation_minutes": 0}]}
        fix_output("materials", data, STAGE_MODELS["materials"])
        STAGE_MODELS["materials"].model_validate(data)
        self.assertEqual([m["print_required"] for m in data["materials"]], [True, False])

    def test_role_typo_in_plan_block(self):
        data = {"roles": [{"role_id": "teacher_1"}, {"role_id": "pupils_all"}],
                "blocks": [{"block_id": "block_02", "role_ids": ["teacher_1", "pups_all"]}]}
        fixes = fix_output("scenario_plan", data, STAGE_MODELS["scenario_plan"])
        self.assertEqual(data["blocks"][0]["role_ids"], ["teacher_1", "pupils_all"])
        self.assertIn({"kind": "ref_fixed", "path": "blocks[0].role_ids", "from": "pups_all", "to": "pupils_all"}, fixes)

    def test_key_with_russian_tail(self):
        data = {"material_id": "m", "used_in блоков": ["block_01"]}
        from app.generation.lenient import _fix_dict
        from app.contracts.llm import Material
        fixes: list = []
        _fix_dict(data, Material, "", fixes)
        self.assertEqual(data.get("used_in_blocks"), ["block_01"])


class PipelineGateTest(unittest.TestCase):
    def run_with(self, output_fixes: str):
        """Эталон Дня знаний с ошибками 3 Pro в плане: раздел рядом с `concept` и опечатка в ключе блока."""
        class Broken(FixtureLLM):
            def generate(self, **kwargs):
                result = super().generate(**kwargs)
                if kwargs["task_name"] == "scenario_plan":
                    data = extract_json(result.text)
                    data["values_to_mechanics"] = data["concept"].pop("values_to_mechanics")
                    data["blocks"][0]["proputed_minutes"] = data["blocks"][0].pop("proposed_minutes")
                    result = dataclasses.replace(result, text=json.dumps(data, ensure_ascii=False))
                return result

        client = Broken([golden("ex1_knowledge_day")])
        client.output_fixes = output_fixes
        gen = Generator(settings(), catalog(), client)
        return gen.run(request("ex1_knowledge_day"))

    def test_lenient_profile_completes(self):
        self.assertEqual(self.run_with("lenient").project["status"], "completed")

    def test_strict_profile_unchanged(self):
        """Тот же ответ у профиля без флага не чинится: как и раньше, план не проходит схему."""
        self.assertEqual(self.run_with("strict").project["status"], "failed")


if __name__ == "__main__":
    unittest.main()
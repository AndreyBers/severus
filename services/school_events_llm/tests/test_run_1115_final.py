"""Финальные прогоны 15.11 на GigaChat-2-Max (variants_1115).

- Первый (24 варианта из 25), День защитника Отечества, вариант 1: этап материалов три раза подряд вернул один
  и тот же ответ байт в байт с `"audience": "whole_class"` у шаблона плаката, схема его не пропускала, и вариант
  не собрался. Адресат «весь класс» - это `pupils_group`.
- Второй (25 из 25), День Свердловской области, вариант 1: «указом губернатора Свердловской области (№ 1022-УГ
  от 23 сентября 2008 года)» - номер указа с пробелом после «№» давал FACT-UNREGISTERED на «1022», а после
  этой правки - на «2008». Дата указа есть в названии источника каталога («от 23.09.2008 № 1022-УГ»), это не новый факт.
- Третий (25 из 25): расходники вне словаря попадали в заметку педагогу по-английски («Также понадобится: colored
  pensils», «sequins, ленты, cardboard figures», «audience ballot»), а в шаблоне стены памяти стояла подпись
  «Класс 9-а, 2023 год».
- Четвёртый (25 из 25): два ложных INNER-TIMING. «На занятие нам отведено 45 минут» во вводном блоке считалось
  отрезком работы; «Затем каждая группа представит свои находки» - выступлением этого блока, хотя группы выступают
  в следующем («Давайте начнём с вашей группы… (Группа представляет…) …послушаем группу номер два»).
"""

import copy
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.contracts.llm import STAGE_MODELS
from app.generation.dates import YEAR
from app.generation.humanize import blank_template_dates
from app.generation.ids import normalize_dependencies, untranslated_things
from app.generation.plan_fixes import declare_parent_roles
from app.validation.inner_timing import inner_timing_problems
from app.generation.pipeline import _audience, prepare_stage_output
from app.llm.jsonx import extract_json
from app.validation.checks import title_dates, validate_variant
from tests.helpers import catalog, settings
from tests.test_validation_render import setup

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "gigachat_materials_whole_class.txt"


class AudienceTest(unittest.TestCase):
    def test_answer_passes_schema(self):
        data = extract_json(FIXTURE.read_text(encoding="utf-8"))
        with self.assertRaises(ValidationError):
            STAGE_MODELS["materials"].model_validate(data)
        changes = prepare_stage_output("materials", data, set(), set(catalog().dependencies))
        self.assertIn({"kind": "audience_fixed", "material_id": "poster_template", "from": "whole_class", "to": "pupils_group"}, changes)
        STAGE_MODELS["materials"].model_validate(data)

    def test_audience_values(self):
        cases = {"whole_class": "pupils_group", "all_pupils": "pupils_group", "all_students": "pupils_group",
                 "class": "pupils_group", "group": "pupils_group", "pupils_pair": "pupils_group", "pupils_all": "pupils_group",
                 "helper": "parent", "all_parents": "parent", "parent_audience": "parent", "everyone": "all",
                 "all": "all", " All ": "all", "teacher": "teacher", "pupil": "pupil", "unknown": "unknown"}
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(_audience(value), expected)


class DocumentNumberTest(unittest.TestCase):
    def test_number_after_sign_is_not_year(self):
        cases = {"(№ 1022-УГ от 23 сентября 2008 года)": ["2008"], "№1022-УГ": [], "№\u00a01022": [],
                 "в 1961 году": ["1961"], "с 1 января 1700 года": ["1700"]}
        for text, years in cases.items():
            with self.subTest(text=text):
                self.assertEqual([m.group(0) for m in YEAR.finditer(text)], years)


    def test_decree_date_from_source_title(self):
        self.assertEqual(title_dates("Указ Губернатора Свердловской области от 23.09.2008 № 1022-УГ «О праздниках»"),
                         ({"2008"}, {(23, 9)}))
        decree = ("Этот праздник установлен указом губернатора Свердловской области (№ 1022-УГ от 23 сентября 2008 года).")
        self.assertNotIn("FACT-UNREGISTERED", block_issues(decree, "sverdlovsk_oblast_day"))
        # Год, которого нет ни в названиях источников, ни в фактах, по-прежнему даёт предупреждение.
        self.assertIn("FACT-UNREGISTERED", block_issues("Область наградили орденом в 1958 году.", "sverdlovsk_oblast_day"))


class ThingsTest(unittest.TestCase):
    def normalize(self, deps: list[str], other_ids: tuple[str, ...] = ()) -> tuple[dict, list[dict]]:
        data = {"materials": [{"material_id": "kit", "dependencies": deps, "teacher_notes": "Разложите заранее."}]
                + [{"material_id": mid, "dependencies": []} for mid in other_ids]}
        changes: list[dict] = []
        normalize_dependencies(data, set(catalog().dependencies), changes)
        return data["materials"][0], changes

    def test_dictionary_matches(self):
        """Опечатка, синоним и «X_or_Y» - ID словаря, а не заметка."""
        cases = {"colored_pensils": ["colored_pencils"], "audio_player": ["audio"], "sticky_notes_or_tape": ["sticky_notes", "tape"]}
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                material, _ = self.normalize([raw])
                self.assertEqual(material["dependencies"], expected)
                self.assertEqual(material["teacher_notes"], "Разложите заранее.")

    def test_notes_in_russian(self):
        material, _ = self.normalize(["sequins", "ribbons", "cardboard_figures", "large_cardboard_box", "puzzle", "ball", "boxes"])
        self.assertEqual(material["teacher_notes"],
                         "Разложите заранее. Также понадобится: пайетки, ленты, картонные фигурки, большие картонные коробки, пазлы, мяч, коробки.")
        self.assertEqual(untranslated_things(material["teacher_notes"]), [])

    def test_color_of_dictionary_item(self):
        """«red_paper» - бумага из словаря (прогон с правкой промптов: «Также понадобится: red «Бумага А4»»)."""
        material, _ = self.normalize(["red_paper", "blue_paper"])
        self.assertEqual(material["dependencies"], ["paper"])
        self.assertEqual(material["teacher_notes"], "Разложите заранее.")
        material, _ = self.normalize(["large_paper"])
        self.assertNotIn("paper", material["dependencies"])

    def test_material_is_not_dependency(self):
        material, changes = self.normalize(["audience_ballot", "markers"], other_ids=("audience_ballot",))
        self.assertEqual(material["dependencies"], ["markers"])
        self.assertEqual(material["teacher_notes"], "Разложите заранее.")
        self.assertIn({"kind": "dependency_is_material", "material_id": "kit", "value": "audience_ballot"}, changes)

    def test_untranslated_is_warned(self):
        material, _ = self.normalize(["glitter_pens"])
        self.assertEqual(untranslated_things(material["teacher_notes"]), ["glitter pens"])
        n, v = setup("ex1_knowledge_day")
        v["materials"][0]["teacher_notes"] = material["teacher_notes"]
        found = [i for i in validate_variant(v, n, catalog(), settings().generation())
                 if i.code == "TECH-ID-IN-TEXT" and i.location == f"materials.{v['materials'][0]['material_id']}"]
        self.assertEqual(len(found), 1)
        self.assertIn("glitter pens", found[0].message)

    def test_caption_year_blanked(self):
        content = 'Верхний заголовок: "Наша Стена Памяти", внизу подпись: "Класс 9-а, 2023 год". Между ячейками поля.'
        variant = {"materials": [{"material_id": "wall_template", "content": content},
                                 {"material_id": "poster", "content": 'Надпись: "Победа, 1945 год".'}]}
        self.assertEqual(blank_template_dates(variant), [{"field": "materials.wall_template.content", "dates": ["2023 год"]}])
        self.assertEqual(variant["materials"][0]["content"],
                         'Верхний заголовок: "Наша Стена Памяти", внизу подпись: "Класс 9-а, 20__ год". Между ячейками поля.')
        self.assertEqual(variant["materials"][1]["content"], 'Надпись: "Победа, 1945 год".')


class ParentRolesTest(unittest.TestCase):
    PLAN = {"roles": [{"role_id": "teacher_1", "participant_type": "teacher", "title": "Ведущий педагог", "count": 1},
                      {"role_id": "pupils_all", "participant_type": "pupils_group", "title": "Учащиеся", "count": 22},
                      {"role_id": "parent_audience", "participant_type": "parent", "role_mode": "audience",
                       "title": "Родители-зрители", "count": 5}],
            "blocks": [{"block_id": "block_03", "role_ids": ["teacher_1", "pupils_all", "parent_helpers"]},
                       {"block_id": "block_04", "role_ids": ["teacher_1", "pupils_all", "parent_audience"]}]}

    def test_helpers_declared(self):
        """Прогон с правкой промптов, Международный женский день, вариант 1: `parent_helpers` в блоке без роли."""
        plan = copy.deepcopy(self.PLAN)
        changes: list[dict] = []
        declare_parent_roles(plan, True, ["helper", "audience"], 5, changes)
        self.assertIn({"role_id": "parent_helpers", "participant_type": "parent", "role_mode": "helper",
                       "title": "Родители-помощники", "count": 5}, plan["roles"])
        self.assertEqual(changes, [{"kind": "parent_role_declared", "role_id": "parent_helpers", "role_mode": "helper", "count": 5}])

    def test_not_declared_without_request(self):
        for parents_enabled, roles in ((False, ["helper"]), (True, ["audience"])):
            with self.subTest(parents_enabled=parents_enabled, roles=roles):
                plan = copy.deepcopy(self.PLAN)
                declare_parent_roles(plan, parents_enabled, roles, 5, [])
                self.assertEqual(len(plan["roles"]), 3)
        plan = copy.deepcopy(self.PLAN)
        plan["blocks"][0]["role_ids"].append("guest_star")
        declare_parent_roles(plan, True, ["helper", "audience"], 5, [])
        self.assertNotIn("guest_star", {r["role_id"] for r in plan["roles"]})


class InnerTimingTest(unittest.TestCase):
    def test_whole_lesson_is_not_interval(self):
        intro = {"duration_minutes": 5, "pupil_actions": [], "teacher_script":
                 "Сегодня мы будем исследовать документы. На занятие нам отведено 45 минут. Сначала разделимся на четыре группы."}
        self.assertEqual(inner_timing_problems(intro, groups_count=4, pairs_count=0, next_duration=15), [])
        for text in ("Наш классный час продлится 30 минут.", "Урок рассчитан на 40 минут."):
            with self.subTest(text=text):
                block = {"duration_minutes": 5, "pupil_actions": [], "teacher_script": text}
                self.assertEqual(inner_timing_problems(block, groups_count=1, pairs_count=0, next_duration=10), [])
        # Отрезок работы, а не всё занятие, по-прежнему считается.
        work = {"duration_minutes": 5, "pupil_actions": [], "teacher_script": "На выполнение задания у вас 25 минут."}
        self.assertTrue(inner_timing_problems(work, groups_count=1, pairs_count=0, next_duration=10))

    def test_groups_present_in_next_block(self):
        block = {"duration_minutes": 15, "pupil_actions": ["Изучают материалы в малой группе"], "teacher_script":
                 "«Сейчас вы получите комплекты документов. На это вам даётся 10 минут. Затем каждая группа представит свои находки классу.»"}
        next_text = ("(Подходит к группе 1) \"Ребята, давайте начнём с вашей группы. Что интересного вы нашли?\" "
                     "(Группа представляет, учитель фиксирует ключевые моменты) \"Теперь послушаем группу номер два.\"")
        self.assertEqual(inner_timing_problems(block, groups_count=6, pairs_count=0, next_duration=10,
                                               next_title="Обсуждение находок", next_text=next_text), [])
        # Если в следующем блоке групп не слушают, выступления остаются частью этого блока.
        self.assertTrue(inner_timing_problems(block, groups_count=6, pairs_count=0, next_duration=10,
                                              next_title="Создание постера", next_text="Теперь все вместе соберём общий постер."))


def block_issues(text: str, event_id: str) -> set[str]:
    n, v = setup("ex1_knowledge_day")
    n = copy.copy(n)
    n.event_id = event_id
    v["timeline"][1]["teacher_script"] = text
    v["fact_claims"] = []
    return {i.code for i in validate_variant(v, n, catalog(), settings().generation())
            if i.location == f"timeline.{v['timeline'][1]['block_id']}"}


if __name__ == "__main__":
    unittest.main()
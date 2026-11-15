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
"""

import copy
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.contracts.llm import STAGE_MODELS
from app.generation.dates import YEAR
from app.generation.humanize import blank_template_dates
from app.generation.ids import normalize_dependencies, untranslated_things
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
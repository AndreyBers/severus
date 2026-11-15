"""Финальные прогоны 15.11 на GigaChat-2-Max (variants_1115).

- Первый (24 варианта из 25), День защитника Отечества, вариант 1: этап материалов три раза подряд вернул один
  и тот же ответ байт в байт с `"audience": "whole_class"` у шаблона плаката, схема его не пропускала, и вариант
  не собрался. Адресат «весь класс» - это `pupils_group`.
- Второй (25 из 25), День Свердловской области, вариант 1: «указом губернатора Свердловской области (№ 1022-УГ
  от 23 сентября 2008 года)» - номер указа с пробелом после «№» давал FACT-UNREGISTERED на «1022», а после
  этой правки - на «2008». Дата указа есть в названии источника каталога («от 23.09.2008 № 1022-УГ»), это не новый факт.
"""

import copy
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.contracts.llm import STAGE_MODELS
from app.generation.dates import YEAR
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
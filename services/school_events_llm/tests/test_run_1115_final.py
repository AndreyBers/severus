"""Финальный прогон 15.11 на GigaChat-2-Max (variants_1115, 24 варианта из 25): День защитника Отечества, вариант 1.

Этап материалов три раза подряд вернул один и тот же ответ байт в байт с `"audience": "whole_class"`
у шаблона плаката, схема его не пропускала, и вариант не собрался. Адресат «весь класс» - это `pupils_group`.
"""

import unittest
from pathlib import Path

from pydantic import ValidationError

from app.contracts.llm import STAGE_MODELS
from app.generation.pipeline import _audience, prepare_stage_output
from app.llm.jsonx import extract_json
from tests.helpers import catalog

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


if __name__ == "__main__":
    unittest.main()
"""Прогоны 15.11 после правки промптов (variants_1115, два раза): технических ID в ответах модели не было,
остались две ложные тревоги самих проверок.

- DOC-UNSOURCED на «Пётр I приказал отмечать Новый год с 1 января 1700 года»: глагол «приказал» принимался
  за документ «приказ». Факт верный: во фрагменте «постановил начать год с 1 января 1700 года».
- FACT-UNREGISTERED на «традиция смотреть мультфильмы всей семьёй вечером 31 декабря»: дата праздника есть
  в карточке каталога, но цифрами («12-31», «31.12»), а сравнивалась строка «31 декабря».
"""

import copy
import unittest

from app.generation.source_refs import document_mentions
from app.validation.checks import event_days, validate_variant
from tests.helpers import catalog, settings
from tests.test_validation_render import setup

PETER = "Петр I приказал отмечать Новый год с 1 января 1700 года."
CARTOONS = "А у кого-то есть традиция смотреть мультфильмы всей семьёй вечером 31 декабря."


def issues(text: str, event_id: str = "new_year") -> set[str]:
    n, v = setup("ex1_knowledge_day")
    n = copy.copy(n)
    n.event_id = event_id
    v["timeline"][1]["teacher_script"] = text
    v["fact_claims"] = [{"claim_id": "fc_01", "text": "а потом постановил начать год с 1 января 1700 года.",
                         "location": f"timeline.{v['timeline'][1]['block_id']}.teacher_script",
                         "source_id": "src_new_year_v19_01", "fragment_id": "frag_new_year_001", "needs_teacher_check": False}]
    return {i.code for i in validate_variant(v, n, catalog(), settings().generation())
            if i.location == f"timeline.{v['timeline'][1]['block_id']}"}


class DocumentWordTest(unittest.TestCase):
    def test_verbs_and_adjectives_are_not_documents(self):
        for text in (PETER, "Как указал губернатор в 2008 году.", "Законный представитель подписывает согласие в 2024 году.",
                     "Мама вышла из декретного отпуска в 2020 году."):
            with self.subTest(text=text):
                self.assertEqual(document_mentions(text), [])

    def test_documents_still_found(self):
        for text, stem in (("Приказом директора от 1 сентября 2024 года.", "приказ"),
                           ("Указом губернатора № 1022-УГ установлен праздник.", "указ"),
                           ("Закон Свердловской области 2010 года.", "закон"),
                           ("Постановлением правительства от 5 мая 2015 года.", "постановлени")):
            with self.subTest(text=text):
                self.assertEqual([found for _, found in document_mentions(text)], [stem])

    def test_trace_phrase(self):
        self.assertNotIn("DOC-UNSOURCED", issues(PETER))


class EventDaysTest(unittest.TestCase):
    def test_card_dates_any_format(self):
        self.assertEqual(event_days({"type": "fixed", "value": "12-31", "note": "Период 31.12 – 08.01; школьные мероприятия - до каникул"}),
                         {(31, 12), (8, 1)})
        self.assertEqual(event_days({"type": "fixed", "value": "01-07", "note": "Ежегодно, 7 января"}), {(7, 1)})
        # Дата указа в пояснении - не день события.
        self.assertEqual(event_days({"type": "variable", "value": "первое воскресенье сентября",
                                     "note": "Дата закреплена Указом Губернатора от 08.09.2016 № 512-УГ."}), set())

    def test_trace_phrase(self):
        """«31 декабря» в Новый год - день самого праздника; другая дата без источника - по-прежнему предупреждение."""
        self.assertNotIn("FACT-UNREGISTERED", issues(CARTOONS))
        self.assertIn("FACT-UNREGISTERED", issues("Говорят, что 12 декабря ёлку наряжали во дворце."))


if __name__ == "__main__":
    unittest.main()
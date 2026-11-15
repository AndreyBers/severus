"""Баг-лист QA 15.11 («Что осталось» после main + PR #30 на 036f713): BUG-20, BUG-23, BUG-06, BUG-04."""

import unittest

from app.generation.ids import normalize_dependencies
from app.generation.pipeline import Generator
from app.llm.fixture import FixtureLLM
from app.validation.checks import Issue, validate_variant
from app.validation.inner_timing import inner_timing_problems
from app.validation.issue_format import category, issue_report
from tests.helpers import catalog, golden, request, settings
from tests.test_validation_render import setup


def timing(text: str, minutes: int, groups: int, next_text: str = "") -> list[str]:
    block = {"duration_minutes": minutes, "pupil_actions": [], "teacher_script": text}
    return inner_timing_problems(block, groups_count=groups, pairs_count=0, next_duration=5, next_text=next_text)


class Bug20Test(unittest.TestCase):
    """INNER-TIMING складывал обсуждение групп и короткие ответы как выступления."""

    def test_discussion_before_class(self):
        """job_20261115_123555_b0c44a, День защитника, block_01: «примерно 2 минуты, чтобы обсудить» - работа групп."""
        text = ("Сейчас я попрошу вас разделиться на ваши группы. У каждой группы есть примерно 2 минуты, чтобы обсудить "
                "два вопроса: Что значит быть защитником? Через 2 минуты мы соберем ваши мысли и обсудим их вместе.")
        self.assertEqual(timing(text, 5, 5), [])

    def test_brief_answers(self):
        """job_20261115_125732_3adb26, Новый год, v2, block_04: 2 минуты обсуждения и по одному моменту от 5 групп в 5 минутах."""
        text = ("Давайте разделимся на наши группы. У вас есть 2 минуты, чтобы обсудить, какие традиции есть в вашей семье, "
                "и записать самое интересное на листах. Потом каждая группа расскажет нам по одному самому интересному моменту.")
        self.assertEqual(timing(text, 5, 5), [])
        self.assertEqual(timing("У вас 7 минут на рисунок. Затем каждая группа коротко покажет свою работу.", 10, 5), [])

    def test_presentation_without_brevity_stays(self):
        """Тот же День защитника, block_02: 7 минут на портрет, потом показ 5 групп в 10 минутах - около 36 секунд на группу."""
        text = ("Ваша задача - обсудить в группе качества защитника и нарисовать его портрет. У вас есть 7 минут на выполнение "
                "этой творческой части. Когда закончите, каждая группа представит свой вариант.")
        self.assertEqual(timing(text, 10, 5), ["после 7 мин работы на выступления 5 групп остаётся 3 мин"])


class Bug23Test(unittest.TestCase):
    """job_b56da75d30c44767b5823d50f90f81b1: «Также понадобится: краски, кисти, water cups, tissues»."""

    def test_art_supplies_in_russian(self):
        data = {"materials": [{"material_id": "art_supplies", "teacher_notes": "Организуйте материалы.",
                               "dependencies": ["colored_pencils", "markers", "paints", "brushes", "water_cups", "tissues"]}]}
        normalize_dependencies(data, set(catalog().dependencies), [])
        self.assertEqual(data["materials"][0]["teacher_notes"],
                         "Организуйте материалы. Также понадобится: краски, кисти, стаканчики для воды, салфетки.")

    def test_message_is_not_about_ids(self):
        n, v = setup("ex1_knowledge_day")
        v["materials"][0]["teacher_notes"] = "Также понадобится: краски, water cups, tissues."
        found = [i for i in validate_variant(v, n, catalog(), settings().generation()) if i.code == "TECH-ID-IN-TEXT"]
        self.assertEqual([i.message for i in found], ["В заметке «Также понадобится» остались слова не по-русски: tissues, water cups"])


class Bug06Test(unittest.TestCase):
    """Формат замечания по ТЗ 16.2: issue_id, category, repairable, suggested_action."""

    def test_fields(self):
        issues = [Issue("RESOURCE-INTERNET", "critical", "timeline.block_04", "Нужен интернет"),
                  Issue("INNER-TIMING", "warning", "timeline.block_02", "Время не сходится", repairable=False),
                  Issue("ROLE-UNUSED", "warning", "roles", "Роль не используется")]
        self.assertEqual(issue_report(issues)[0], {
            "issue_id": "Q-001", "code": "RESOURCE-INTERNET", "severity": "critical", "category": "resources",
            "location": "timeline.block_04", "message": "Нужен интернет", "repairable": True,
            "suggested_action": "Заменить онлайн-задание на офлайн-вариант"})
        self.assertEqual([(i["issue_id"], i["category"], i["repairable"]) for i in issue_report(issues)[1:]],
                         [("Q-002", "timing", False), ("Q-003", "roles", True)])
        self.assertIsNone(issue_report(issues)[2]["suggested_action"])
        self.assertEqual(category("NEW-CODE"), "other")

    def test_in_project(self):
        project = Generator(settings(), catalog(), FixtureLLM([golden("ex1_knowledge_day")])).run(request("ex1_knowledge_day")).project
        for variant in project["variants"]:
            for issue in variant["quality_report"]["issues"]:
                self.assertTrue({"issue_id", "code", "severity", "category", "location", "message", "repairable",
                                 "suggested_action"} <= set(issue))


class Bug04Test(unittest.TestCase):
    """Тестовый режим: эталон того же события первым, а не по порядку."""

    def test_same_event_first(self):
        goldens = [golden(name) for name in ("ex1_knowledge_day", "ex2_mothers_day", "ex3_labour_day")]
        project = Generator(settings(), catalog(), FixtureLLM(goldens)).run(request("ex2_mothers_day")).project
        self.assertEqual(project["variants"][0]["title"], golden("ex2_mothers_day")["variant_package"]["variant"]["title"])

    def test_order(self):
        goldens = [golden(name) for name in ("ex1_knowledge_day", "ex2_mothers_day", "ex3_labour_day")]
        client = FixtureLLM(goldens)
        self.assertEqual([g["example_id"] for g in client._ordered("labour_day")],
                         [goldens[2]["example_id"], goldens[0]["example_id"], goldens[1]["example_id"]])
        self.assertEqual([g["example_id"] for g in client._ordered(None)], [g["example_id"] for g in goldens])


if __name__ == "__main__":
    unittest.main()
"""Прогон 15.11 «10 генераций по 2-3 варианта» (variants_1115): поиск ID по ступеням, кусок JSON со ссылками
в тексте, пары, которые разговаривают друг с другом.

- `task_card` в реплике при материале `card_task` (Последний звонок, v2, блок 3) и `commitments_book_pages`
  при `commitment_book_pages` (QA 14.11, BUG-16): ID с другим порядком слов, числом, опечаткой.
- Карточка станции (День Свердловской области, v2): модель вписала в текст
  «fact_claims: [ { "source_id": …, "fragment_id": … } ]», после чистки оставался пустой каркас.
- «10 пар × 2 мин» (Новый год, v3, блок 2): пары рассказывают друг другу одновременно.
"""

import unittest

from app.generation.humanize import IdMatcher, humanize_text, humanize_variant
from app.generation.source_refs import move_source_refs
from app.validation.inner_timing import inner_timing_problems
from tests.helpers import catalog

# Реплика блока 3 из трассы (Последний звонок, v2), сокращена.
LAST_BELL = ("Ваша задача - разгадать их вместе и найти буквы, спрятанные в классе. Готовы? Тогда начинаем! "
             "(раздаёт карточки task_card) У вас 15 минут.")

# Карточка станции из ответа модели (День Свердловской области, v2), первые две станции.
STATION_CARDS = """Карточка Станции 1: Исторический центр Екатеринбурга
Вопрос: Почему 17 января 1934 года стало важным днем для нашей области?
Правильный ответ: В этот день Уральская область была разделена на Свердловскую, Челябинскую и Обско-Иртышскую области.
fact_claims: [
  {
    "source_id": "src_sverdlovsk_oblast_day_regional_01",
    "fragment_id": "frag_sverdlovsk_001"
  },
  {
    "source_id": "src_sverdlovsk_oblast_day_regional_02",
    "fragment_id": "frag_sverdlovsk_002"
  }
]

Карточка Станции 2: Музей истории города
Вопрос: Найдите три интересных факта о нашем городе."""

CLEAN_CARDS = """Карточка Станции 1: Исторический центр Екатеринбурга
Вопрос: Почему 17 января 1934 года стало важным днем для нашей области?
Правильный ответ: В этот день Уральская область была разделена на Свердловскую, Челябинскую и Обско-Иртышскую области.

Карточка Станции 2: Музей истории города
Вопрос: Найдите три интересных факта о нашем городе."""

# Блок 2 (7 мин) из трассы (Новый год, v3), 10 пар.
PAIRS_TALK = ("Давайте сейчас поделимся друг с другом, какие интересные традиции есть в ваших семьях. Я предлагаю вам "
              "объединиться в пары. (Педагог помогает ученикам разделиться на пары.) Сейчас у каждой пары будет по две "
              "минуты, чтобы поделиться тем, что вы узнали о новогодних традициях вашей семьи. Начинаем! (Через две минуты) "
              "Спасибо, ребята, очень интересно было послушать ваши рассказы.")

# Блок 4 (10 мин) из той же генерации (Победа, v3), 12 пар выступают перед классом.
PAIRS_PRESENT = ("Сейчас мы послушаем друг друга. Каждая пара представит свой вариант, коротко и чётко - максимум одна минута "
                 "на каждую пару. Остальные внимательно слушают, а потом мы выберем самые интересные предложения.")


def names(*ids: str) -> dict[str, str]:
    return {key: f"«{key}»" for key in ids}


class IdMatcherTest(unittest.TestCase):
    def test_steps(self):
        matcher = IdMatcher(names("card_task", "commitment_book_pages", "station_cards_set"))
        cases = {
            "card_task": ("card_task", "exact"),
            "task_card": ("card_task", "words"),
            "commitments_book_pages": ("commitment_book_pages", "words"),
            "station_card": ("station_cards_set", "extra_word"),
            "commitmnet_book_pages": ("commitment_book_pages", "typo"),
            "commitment_bok_pages": None,  # «bok» короче 5 букв: не опечатка, а другое слово
        }
        for token, expected in cases.items():
            with self.subTest(token=token):
                found = matcher.find(token)
                self.assertEqual(found[1:] if found else None, expected)
        self.assertEqual(matcher.find("colored_cardboards"), ("цветной картон", None, "dictionary"))

    def test_no_guessing(self):
        """Похожие, но другие слова, слово со смыслом, два кандидата, другая цифра - не подставляются."""
        matcher = IdMatcher(names("station_cards", "vote_cards", "quiz_cards", "team_card_big", "team_card_set", "block_03"))
        for token in ("situation_cards", "route_cards", "quiz_answer_cards", "team_cards", "block_04", "magic_box"):
            with self.subTest(token=token):
                self.assertIsNone(matcher.find(token))

    def test_roles_only_exact(self):
        """Памятка помощникам - не роль «parent_helpers»: роли и блоки нестрого не ищутся."""
        matcher = IdMatcher(names("parent_helpers", "station_cards"), fuzzy_keys={"station_cards"})
        self.assertIsNone(matcher.find("parent_helper_instructions"))
        self.assertEqual(matcher.find("parent_helpers")[1:], ("parent_helpers", "exact"))

    def test_trace_block_and_record(self):
        """Реплика из трассы: «task_card» - название материала «card_task»; нестрогая замена видна в трассе."""
        variant = {"timeline": [{"block_id": "block_03", "title": "Квест", "purpose": "", "teacher_script": LAST_BELL,
                                 "pupil_actions": []}],
                   "materials": [{"material_id": "card_task", "title": "Карточки заданий", "content": "", "teacher_notes": ""}],
                   "roles": [], "teacher_instructions": []}
        changes = humanize_variant(variant)
        self.assertIn("(раздаёт «Карточки заданий»)", variant["timeline"][0]["teacher_script"])
        self.assertEqual(changes, [{"field": "timeline.block_03.teacher_script", "ids": ["task_card"],
                                    "matched": {"task_card": "card_task (words)"}}])

    def test_plain_text_untouched(self):
        text = "Откройте https://example.org/task_card и файл task_card.pdf; формула x_1 + y_2."
        self.assertEqual(humanize_text(text, names("card_task")), (text, []))


class RefJsonTest(unittest.TestCase):
    def fragments(self):
        return catalog().verified_fragments("sverdlovsk_oblast_day", "RU-SVE")

    def variant(self, content):
        return {"timeline": [], "teacher_instructions": [], "fact_claims": [],
                "materials": [{"material_id": "station_cards", "content": content, "teacher_notes": ""}]}

    def test_trace_card(self):
        variant = self.variant(STATION_CARDS)
        changes = move_source_refs(variant, self.fragments())
        self.assertEqual(variant["materials"][0]["content"], CLEAN_CARDS)
        self.assertEqual(changes[0]["field"], "materials.station_cards.content")

    def test_empty_skeleton(self):
        """Каркас без ID (так он выглядел в готовом варианте после прежней чистки) тоже убирается."""
        skeleton = STATION_CARDS.replace("src_sverdlovsk_oblast_day_regional_01", "").replace("src_sverdlovsk_oblast_day_regional_02", "")
        skeleton = skeleton.replace("frag_sverdlovsk_001", "").replace("frag_sverdlovsk_002", "").replace("fact_claims: ", "")
        variant = self.variant(skeleton)
        move_source_refs(variant, self.fragments())
        self.assertEqual(variant["materials"][0]["content"], CLEAN_CARDS)

    def test_fact_before_json_registered(self):
        """Фраза с датой перед куском JSON записывается с фрагментом из него."""
        content = ('17 января 1934 года Уральская область была разделена на Свердловскую, Челябинскую и Обско-Иртышскую области.\n'
                   '[{"source_id": "src_sverdlovsk_oblast_day_regional_02", "fragment_id": "frag_sverdlovsk_002"}]')
        variant = self.variant(content)
        move_source_refs(variant, self.fragments())
        self.assertEqual(variant["materials"][0]["content"], content.split("\n")[0])
        self.assertEqual([c["fragment_id"] for c in variant["fact_claims"]], ["frag_sverdlovsk_002"])

    def test_other_braces_untouched(self):
        content = "Заполните таблицу {имя, класс} и список [1, 2, 3]."
        variant = self.variant(content)
        self.assertEqual(move_source_refs(variant, self.fragments()), [])
        self.assertEqual(variant["materials"][0]["content"], content)


class PairsTalkTest(unittest.TestCase):
    def test_pairs_talk_to_each_other(self):
        block = {"duration_minutes": 7, "teacher_script": PAIRS_TALK,
                 "pupil_actions": ["Дети делятся на пары.", "Каждый рассказывает партнёру о семейных новогодних традициях."]}
        self.assertEqual(inner_timing_problems(block, groups_count=1, pairs_count=10, next_duration=10), [])

    def test_pairs_present_to_class_still_flagged(self):
        block = {"duration_minutes": 10, "teacher_script": PAIRS_PRESENT, "pupil_actions": []}
        self.assertEqual(inner_timing_problems(block, groups_count=1, pairs_count=12),
                         ["выступления: 12 пар × 1 мин = 12 мин, а на блок 10 мин"])


if __name__ == "__main__":
    unittest.main()
"""Детерминированное деление учащихся на группы (ТЗ 12.3)."""

from __future__ import annotations

import math
import re


def split_even(total: int, groups: int) -> list[int]:
    """27 на 5 → [6, 6, 5, 5, 5]: размеры отличаются не больше чем на 1, крупные первыми."""
    groups = max(1, min(groups, total))
    base, rem = divmod(total, groups)
    return [base + 1] * rem + [base] * (groups - rem)


def pairs(total: int) -> list[int]:
    """Пары; при нечётном числе одна тройка: 27 → 12×2 + 1×3."""
    if total < 2:
        return [total]
    count = total // 2
    sizes = [2] * count
    if total % 2:
        sizes[-1] = 3
    return sizes


def compute_grouping(mode: str, total: int, groups_count: int, group_work: bool) -> tuple[str, list[int], list[str]]:
    """Возвращает (режим, размеры, предупреждения). При group_work=false малые группы заменяются."""
    notes: list[str] = []
    if mode in ("small_groups", "mixed") and not group_work:
        notes.append("Обязательные малые группы запрещены: режим заменён на whole_class")
        mode = "whole_class"
    if mode == "whole_class":
        return mode, [total], notes
    if mode == "pairs":
        return mode, pairs(total), notes
    if groups_count < 2:
        groups_count = max(2, round(total / 5))
        notes.append(f"Число групп не указано или меньше 2 - выбрано {groups_count}")
    return mode, split_even(total, groups_count), notes


def plural(n: int, one: str, few: str, many: str) -> str:
    """Форма слова после числа: 1 группа, 2 группы, 5 групп, 21 группа, 11 групп."""
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def describe(sizes: list[int]) -> str:
    """Преобразует рассчитанные размеры групп в понятное текстовое описание.

    Параметры:
        `sizes`.

    Возвращает:
        str.
    """
    if len(sizes) == 1:
        return f"весь класс ({sizes[0]})"
    if all(s == 2 for s in sizes[:-1]) and sizes[-1] in (2, 3) and len(sizes) > 2:
        tail = " и одна тройка" if sizes[-1] == 3 else ""
        pairs = len(sizes) - (1 if sizes[-1] == 3 else 0)
        return f"{pairs} {plural(pairs, 'пара', 'пары', 'пар')}{tail}"
    return f"{len(sizes)} {plural(len(sizes), 'группа', 'группы', 'групп')}: " + ", ".join(str(s) for s in sizes)


# Какие блоки получают строку про выступления: по названию и цели блока плана.
_PRESENT = re.compile(r"выступ|презент|представ|защит|инсцен|ярмарк|показ", re.I)
_GROUP_WORK = re.compile(r"групп|команд|\bпар(?:а|ы|ах|ами|у)?\b|в парах|станци|совместн|мастерск", re.I)
_ORGANIZE = re.compile(r"формирован|организац|делени|распредел|выбор|знакомств|приветств|вступлен|введени|объяснени|рефлекс|итог|заверш"
                       r"|(?:создани|сбор)\w*\s+(?:команд|групп)", re.I)


def presentation_budget(mode: str, sizes: list[int], block: dict, minutes: int, grouping_block_ids: list[str],
                        next_block: dict | None = None) -> str:
    """Минуты на выступление каждой группы или пары для строки блока в промпте; не тот блок - пустая строка.

    Четыре финальных прогона и два прогона с правкой промптов 15.11: настоящие INNER-TIMING - все «12 пар по
    3 минуты в блоке на 20 минут», «6 минут работы и выступления 4 групп в 8 минутах». Общее правило «число
    выступающих × минуты не больше длительности» модель сама не считает, поэтому числа даёт программа.
    Только числа, без готовых решений («по желанию»): образец с одним значением модель копирует.

    Строку получают блоки выступлений («Представление проектов») и блоки работы групп или пар, после которых
    нет блока выступлений. Не получают: организационные блоки (формирование команд, приветствие, итоги),
    блоки короче 4 минут и работа групп перед блоком выступлений - чтобы модель не добавляла туда выступления.
    """
    if mode == "whole_class" or len(sizes) < 2 or minutes < 4:
        return ""
    text = f"{block.get('title') or ''} {block.get('purpose') or ''}"
    if _ORGANIZE.search(str(block.get("title") or "")):
        return ""
    presents_next = bool(next_block) and bool(_PRESENT.search(f"{next_block.get('title') or ''} {next_block.get('purpose') or ''}"))
    group_work = block.get("block_id") in grouping_block_ids or bool(_GROUP_WORK.search(text))
    if not _PRESENT.search(text) and not (group_work and not presents_next):
        return ""
    units = len(sizes)
    who = f"всех {units} {plural(units, 'пары', 'пар', 'пар') if mode == 'pairs' else plural(units, 'группы', 'групп', 'групп')}"
    per = math.floor((minutes - 1) / units * 2) / 2
    if per < 1:
        # Меньше минуты - в секундах: 12 пар за 10 минут - около 45 секунд, для короткого ответа это реально.
        # Прогон с минутами в промпте: на «меньше 1 мин - не успеют» модель всё равно слушала все пары.
        seconds = math.floor((minutes - 1) * 60 / units / 5) * 5
        if seconds >= 30:
            return f"выступления {who}: около {seconds} сек на каждую; работа до них тоже входит в {minutes} мин"
        return f"выступления {who}: меньше 30 сек на каждую - все за {minutes} мин не успеют"
    per_txt = str(int(per)) if per == int(per) else str(per).replace(".", ",")
    return f"выступления {who}: не больше {per_txt} мин на каждую; работа до них тоже входит в {minutes} мин"
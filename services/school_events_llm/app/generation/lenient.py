"""Поблажки к форме ответа для моделей, которые пишут JSON небрежно (профиль с `"output_fixes": "lenient"`).

Прогон GigaChat-3-Pro 15.11 (variants_1115): 0 генераций из 10, 64 отказа схемы из 96 вызовов. Содержание
в ответах полное, ломается форма, и повтор с подсказкой не помогает (9 из 26 повторов - тот же ответ байт в байт):
- опечатки в ключах: `proputed_minutes`, `used_inblocks`, `narrative_approch`, `values_to_mechanики`;
- раздел не на своём месте: `values_to_mechanics` рядом с `concept`, а не внутри него;
- словарь вместо списка: `"key_activities": {"activity_type": "game", "description": "…"}`;
- пропущенные поля, которые программа знает из плана: `role_ids` блока, `used_in_blocks` материала.

Здесь всё это чинится по схеме этапа (Pydantic-модели) и по плану, без угадывания содержания:
1. Ключ, которого нет в схеме, переименовывается в недостающее поле схемы, если это явно оно: те же буквы
   без подчёркиваний, опечатка в 1-2 буквы у длинного имени, латинское начало перед русскими буквами.
   Только при единственном кандидате.
2. Недостающее поле вложенного раздела берётся с уровня выше, если там оно лишнее (`values_to_mechanics`).
3. Словарь на месте списка - список: один элемент или значения словаря (ключ - `activity_type`, если его нет).
4. Значение не из списка допустимых: «teacher | pupils_group» (строка из образца) - первый допустимый вариант,
   «pupils_all» - вариант с тем же первым словом («pupils_group»), если он один.
5. Из плана: `role_ids` блока, `used_in_blocks` материала; `purpose` блока или материала - его название.
6. Второй прогон 3 Pro 15.11 (19 вариантов из 25): `print_required` материала - по расходникам (печатать, если
   в `dependencies` есть принтер); ID роли с опечаткой в блоке плана (`pups_all`) - объявленная роль (`pupils_all`).

У профилей без флага (GigaChat-2-Max и другие) ничего из этого не вызывается: их работа не меняется.
"""

from __future__ import annotations

import re
import typing
from typing import Any

from pydantic import BaseModel

_LETTERS = re.compile(r"[^a-z]")
# Ключ, похожий на поле другого раздела: «approx_minutes» у блока плана - это «proposed_minutes».
_ALIASES = {"approx_minutes": "proposed_minutes", "minutes": "proposed_minutes", "description": "purpose"}
# Перечисления, которые уже чинит общий `prepare_stage_output` (механики, типы занятий и материалов, режимы):
# их здесь не трогаем, чтобы замена была та же, что и у остальных моделей.
_ENUMS_FIXED_ELSEWHERE = {"engagement_mode", "primary_mechanic", "activity_type", "mechanic_type", "mode", "role_mode", "type"}


def _distance(a: str, b: str, limit: int = 2) -> int:
    """Расстояние Левенштейна; больше `limit` не считается точно (возвращается `limit + 1`)."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


def _same_key(unknown: str, field: str) -> bool:
    """`unknown` - это `field` с ошибкой: «used_inblocks», «proputed_minutes», «values_to_mechanики»."""
    u, f = _LETTERS.sub("", unknown.lower()), _LETTERS.sub("", field.lower())
    if not u:
        return False
    if u == f or (len(f) >= 8 and _distance(u, f) <= 2):
        return True
    latin = re.match(r"[A-Za-z_]+", unknown)
    prefix = _LETTERS.sub("", latin.group(0).lower()) if latin and latin.end() < len(unknown) else ""
    # Латинское начало перед русскими буквами - хотя бы половина имени: «used_in блоков», «values_to_mechanики».
    return len(prefix) >= 6 and f.startswith(prefix) and len(prefix) >= 0.5 * len(f)


def _model_of(annotation: Any) -> type[BaseModel] | None:
    """Вложенная модель поля: `list[Concept]`, `Concept | None` -> Concept; у строк и чисел - None."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for arg in typing.get_args(annotation):
        model = _model_of(arg)
        if model is not None:
            return model
    return None


def _is_list(annotation: Any) -> bool:
    if typing.get_origin(annotation) in (list, typing.List):
        return True
    return any(typing.get_origin(arg) in (list, typing.List) for arg in typing.get_args(annotation))


def _fix_dict(data: dict, model: type[BaseModel], path: str, fixes: list[dict]) -> None:
    fields = model.model_fields
    # 1. Ключи с ошибкой и ключи-синонимы.
    missing = [name for name in fields if name not in data]
    unknown = [key for key in data if key not in fields]
    for name in missing:
        candidates = [key for key in unknown if _same_key(key, name)]
        if len(candidates) == 1 and sum(_same_key(candidates[0], other) for other in missing) == 1:
            data[name] = data.pop(candidates[0])
            unknown.remove(candidates[0])
            fixes.append({"kind": "key_renamed", "path": path, "from": candidates[0], "to": name})
    # Значение без ключа (`quote_keys` дал ему ключ `_orphan_N`): если не хватает ровно одного строкового поля -
    # это оно: `{"order": 3, "планирование и сборка", "activity_type": …}` - пропущен `title`.
    orphans = [key for key in data if key.startswith("_orphan_") and isinstance(data[key], str)]
    text_fields = [name for name in fields if name not in data and fields[name].is_required() and fields[name].annotation is str]
    if len(orphans) == 1 and len(text_fields) == 1:
        data[text_fields[0]] = data.pop(orphans[0])
        fixes.append({"kind": "value_keyed", "path": path, "to": text_fields[0]})
    for alias, name in _ALIASES.items():
        if name in fields and name not in data and alias in data and alias not in fields:
            data[name] = data.pop(alias)
            fixes.append({"kind": "key_renamed", "path": path, "from": alias, "to": name})
    # Значение не из списка допустимых: «teacher | pupils_group» (модель переписала строку из образца ответа) -
    # первый допустимый вариант; «pupils_all» (ID роли) - вариант с тем же первым словом, если он один.
    for name, info in fields.items():
        options = () if name in _ENUMS_FIXED_ELSEWHERE else _literal_options(info.annotation)
        value = data.get(name)
        if options and isinstance(value, str) and value not in options:
            fixed = _literal_value(value, options)
            if fixed:
                data[name] = fixed
                fixes.append({"kind": "enum_fixed", "path": f"{path}.{name}".lstrip("."), "from": value, "to": fixed})
    # 2-3. Вложенные разделы: поле с уровня выше, словарь вместо списка, рекурсия.
    for name, info in fields.items():
        value = data.get(name)
        nested = _model_of(info.annotation)
        if _is_list(info.annotation) and isinstance(value, dict):
            data[name] = value = _as_list(value, nested)
            fixes.append({"kind": "list_wrapped", "path": f"{path}.{name}".lstrip(".")})
        if nested is None:
            continue
        items = value if isinstance(value, list) else [value]
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            where = f"{path}.{name}" + (f"[{index}]" if isinstance(value, list) else "")
            if not isinstance(value, list):
                for child in nested.model_fields:
                    if child not in item and child in data and child not in fields:
                        item[child] = data.pop(child)
                        fixes.append({"kind": "field_moved", "path": where.lstrip("."), "field": child})
            _fix_dict(item, nested, where.lstrip("."), fixes)


def _literal_options(annotation: Any) -> tuple[str, ...]:
    if typing.get_origin(annotation) is typing.Literal:
        return tuple(str(a) for a in typing.get_args(annotation))
    for arg in typing.get_args(annotation):
        options = _literal_options(arg)
        if options:
            return options
    return ()


def _literal_value(value: str, options: tuple[str, ...]) -> str | None:
    parts = [p.strip() for p in re.split(r"[|,/]", value) if p.strip()]
    for part in parts:
        if part in options:
            return part
    first = re.split(r"[^a-z]", value.lower())[0]
    same = [o for o in options if re.split(r"[^a-z]", o)[0] == first] if first else []
    return same[0] if len(same) == 1 else None


def _as_list(value: dict, nested: type[BaseModel] | None) -> list:
    """Словарь на месте списка: один элемент списка или значения словаря."""
    if nested is not None and set(value) & set(nested.model_fields):
        return [value]
    items = []
    for key, item in value.items():
        if isinstance(item, dict) and nested is not None and "activity_type" in nested.model_fields:
            item = {"activity_type": key, **item}
        items.append(item)
    return items


def _plan_block(plan: dict | None, block_id: str | None) -> dict | None:
    return next((b for b in (plan or {}).get("blocks") or [] if b.get("block_id") == block_id), None)


def fix_output(stage: str, data: Any, model: type[BaseModel], *, plan: dict | None = None,
               block_id: str | None = None) -> list[dict]:
    """Чинит форму ответа этапа по схеме `model` и плану (`plan`, для блоков и материалов). Возвращает список правок."""
    fixes: list[dict] = []
    if not isinstance(data, dict):
        return fixes
    _fix_dict(data, model, "", fixes)
    # 5. Поля, которые программа знает из плана.
    if stage == "scenario_plan":
        declared = [r.get("role_id") for r in data.get("roles") or [] if isinstance(r, dict) and r.get("role_id")]
        for index, block in enumerate(data.get("blocks") or []):
            if isinstance(block, dict) and isinstance(block.get("role_ids"), list):
                for pos, role in enumerate(block["role_ids"]):
                    if isinstance(role, str) and role not in declared:
                        same = [d for d in declared if _same_key(role, d)]
                        if len(same) == 1:
                            block["role_ids"][pos] = same[0]
                            fixes.append({"kind": "ref_fixed", "path": f"blocks[{index}].role_ids", "from": role, "to": same[0]})
            if isinstance(block, dict) and "purpose" not in block and block.get("title"):
                block["purpose"] = block["title"]
                fixes.append({"kind": "filled", "path": f"blocks[{index}].purpose", "from": "title"})
        for index, material in enumerate(data.get("planned_materials") or []):
            if isinstance(material, dict) and "purpose" not in material:
                material["purpose"] = material.get("title") or ""
                fixes.append({"kind": "filled", "path": f"planned_materials[{index}].purpose", "from": "title"})
    blocks = [data["block"]] if stage == "scenario_block" and isinstance(data.get("block"), dict) else (
        [b for b in data.get("blocks") or [] if isinstance(b, dict)] if stage == "scenario_blocks" else [])
    for block in blocks:
        planned = _plan_block(plan, block.get("block_id") or block_id)
        if not block.get("role_ids") and planned and planned.get("role_ids"):
            block["role_ids"] = list(planned["role_ids"])
            fixes.append({"kind": "filled", "path": f"block {block.get('block_id') or block_id}.role_ids", "from": "plan"})
    if stage == "materials":
        for material in data.get("materials") or []:
            if isinstance(material, dict) and "print_required" not in material:
                material["print_required"] = "printer" in (material.get("dependencies") or [])
                fixes.append({"kind": "filled", "path": f"materials.{material.get('material_id')}.print_required",
                              "from": "dependencies"})
            if isinstance(material, dict) and not material.get("used_in_blocks"):
                used = [b["block_id"] for b in (plan or {}).get("blocks") or []
                        if material.get("material_id") in (b.get("planned_material_ids") or [])]
                if used:
                    material["used_in_blocks"] = used
                    fixes.append({"kind": "filled", "path": f"materials.{material.get('material_id')}.used_in_blocks", "from": "plan"})
    return fixes
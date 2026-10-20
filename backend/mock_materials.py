def build_mock_materials(concept: dict) -> list[dict]:
    """Создаёт тестовые текстовые материалы без LLM."""

    entries = [
        (
            "teacher_intro",
            "teacher_instruction",
            "Памятка ведущему",
            "block_01",
            "teacher",
            "Объявите тему встречи и объясните её цель.",
        ),
        (
            "activity_guide",
            "activity_card",
            f"Задание: {concept['activity']}",
            "block_02",
            "pupils_group",
            (
                f"Выполните задание «{concept['activity']}». "
                f"Цель: {concept['goal']}. "
                "Обсудите результат и подготовьте краткий ответ."
            ),
        ),
    ]

    return [
        {
            "material_id": material_id,
            "type": material_type,
            "title": title,
            "used_in_blocks": [block_id],
            "audience": audience,
            "content": content,
            "teacher_notes": "Инструкцию можно зачитать вслух.",
            "print_required": False,
            "dependencies": [],
            "estimated_preparation_minutes": 2,
        }
        for material_id, material_type, title,
            block_id, audience, content in entries
    ]

from backend.schemas import GenerationRequest


def build_mock_timeline(
    request: GenerationRequest,
    concept: dict,
    roles: list[dict],
) -> list[dict]:
    duration = request.duration_minutes

    blocks = [
        {
            "block_id": "block_01",
            "start_minute": 0,
            "duration_minutes": 5,
            "title": "Вступление",
            "purpose": "Познакомить участников с темой",
            "teacher_script": "Объявите тему и цель мероприятия.",
            "pupil_actions": ["Слушают и отвечают на вопросы."],
        },
        {
            "block_id": "block_02",
            "start_minute": 5,
            "duration_minutes": duration - 10,
            "title": concept["activity"],
            "purpose": concept["goal"],
            "teacher_script": (
                f"Организуйте активность: {concept['activity']}."
            ),
            "pupil_actions": [
                f"Выполняют задание: {concept['activity']}."
            ],
        },
        {
            "block_id": "block_03",
            "start_minute": duration - 5,
            "duration_minutes": 5,
            "title": "Подведение итогов",
            "purpose": "Закрепить результаты мероприятия",
            "teacher_script": "Обсудите результаты и подведите итоги.",
            "pupil_actions": ["Делятся выводами и впечатлениями."],
        },
    ]

    for block in blocks:
        block["role_ids"] = [
            role["role_id"]
            for role in roles
            if block["block_id"] in role["block_ids"]
        ]
        block["material_ids"] = []

    return blocks

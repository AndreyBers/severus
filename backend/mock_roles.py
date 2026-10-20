from backend.schemas import GenerationRequest

BLOCK_IDS = ["block_01", "block_02", "block_03"]


def build_mock_roles(request: GenerationRequest) -> list[dict]:
    roles = []

    for number in range(1, request.participants.teachers_count + 1):
        roles.append({
            "role_id": f"teacher_{number}",
            "participant_type": "teacher",
            "title": f"Педагог {number}",
            "count": 1,
            "block_ids": BLOCK_IDS.copy(),
        })

    roles.append({
        "role_id": "pupils_all",
        "participant_type": "pupils_group",
        "title": "Учащиеся",
        "count": request.pupils_count,
        "block_ids": BLOCK_IDS.copy(),
    })

    roles.extend(build_mock_parent_roles(request))
    return roles


PARENT_TITLES = {
    "helper": "Помощники",
    "active_participant": "Активные участники",
    "audience": "Зрители",
    "evaluator": "Оценивающие",
}


def build_mock_parent_roles(request: GenerationRequest) -> list[dict]:
    participants = request.participants

    if not participants.parents_enabled:
        return []

    remaining = participants.parents_count
    modes = participants.parent_roles

    # Зрителям отдаём оставшиеся места.
    modes = [m for m in modes if m != "audience"] + [
        m for m in modes if m == "audience"
    ]

    result = []

    for index, mode in enumerate(modes):
        places_to_reserve = len(modes) - index - 1
        count = (
            remaining if places_to_reserve == 0
            else min(2, max(0, remaining - places_to_reserve))
        )

        if count == 0:
            continue

        result.append({
            "role_id": f"parent_{mode}",
            "participant_type": "parent",
            "role_mode": mode,
            "title": PARENT_TITLES[mode],
            "count": count,
            "block_ids": BLOCK_IDS.copy(),
        })

        remaining -= count

    return result

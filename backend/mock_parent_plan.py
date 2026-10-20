from backend.schemas import GenerationRequest


def build_mock_parent_plan(
    request: GenerationRequest,
    roles: list[dict],
    timeline: list[dict],
    materials: list[dict],
) -> dict | None:
    participants = request.participants

    if not participants.parents_enabled:
        return None

    parent_roles = [
        role for role in roles
        if role["participant_type"] == "parent"
    ]

    count = participants.parents_count
    assert sum(r["count"] for r in parent_roles) == count

    if count <= 2:
        size_group = "1-2"
    elif count <= 5:
        size_group = "3-5"
    elif count <= 10:
        size_group = "6-10"
    else:
        size_group = "11_plus"

    engagement = participants.parent_audience_engagement

    if engagement == "feedback":
        timeline[-1]["teacher_script"] += (
            " Предложите зрителям добровольно поделиться "
            "положительными впечатлениями."
        )

    voting = build_mock_voting(
        engagement, parent_roles, timeline, materials
    )

    return {
        "enabled": True,
        "parents_count": count,
        "parent_size_group": size_group,
        "selected_roles": [r["role_mode"] for r in parent_roles],
        "audience_engagement": engagement,
        "assignments": [
            {
                "role_id": r["role_id"],
                "participant_type": "parent",
                "role_mode": r["role_mode"],
                "count": r["count"],
                "block_ids": r["block_ids"],
            }
            for r in parent_roles
        ],
        "voting": voting,
        "teacher_fallback": (
            "Если родители не пришли, педагог проводит "
            "мероприятие с учениками без зрительского голосования."
        ),
    }


def build_mock_voting(
    engagement: str,
    parent_roles: list[dict],
    timeline: list[dict],
    materials: list[dict],
) -> dict | None:
    if engagement not in ("vote", "audience_award"):
        return None

    voters = sum(
        r["count"] for r in parent_roles
        if r["role_mode"] == "audience"
    )
    if voters == 0:
        return None

    final_block = timeline[-1]
    material_id = "parent_voting_guide"

    materials.append({
        "material_id": material_id,
        "type": "teacher_instruction",
        "title": "Регламент зрительского голосования",
        "used_in_blocks": [final_block["block_id"]],
        "audience": "teacher",
        "content": (
            "Объявите критерий оценки. Каждый зритель "
            "может поднять руку один раз. Подсчитайте "
            "только фактически поданные голоса."
        ),
        "teacher_notes": "Не объявляйте плановое число фактическим.",
        "print_required": False,
        "dependencies": [],
        "estimated_preparation_minutes": 1,
    })

    final_block["material_ids"].append(material_id)
    final_block["teacher_script"] += (
        " Объявите критерий зрительского голосования. "
        "Проведите голосование и подведите итоги."
    )

    return {
        "enabled": True,
        "award_title": (
            "Приз зрительских симпатий"
            if engagement == "audience_award" else None
        ),
        "voters_count_planned": voters,
        "criterion": "Понятность представленного результата",
        "method": "show_of_hands",
        "votes_per_person": 1,
        "tie_rule": "При равенстве голосов отметить оба результата",
        "block_id": final_block["block_id"],
        "material_ids": [material_id],
    }

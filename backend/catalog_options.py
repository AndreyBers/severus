from typing import get_args

from fastapi import APIRouter

from backend.schemas import GenerationRequest, GradeGroup, EventFormat
from backend.participants import ParentRole, AudienceEngagement
from backend.resources import RoomType
from backend.teacher_preferences import TeacherPreferences


router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])

LABELS = {
    "grade_group": {
        "1-4": "1–4 классы",
        "5-8": "5–8 классы",
        "9-11": "9–11 классы",
    },
    "format": {
        "class_hour": "Классный час",
        "school_event": "Общешкольное мероприятие",
        "interactive_lesson": "Интерактивное занятие",
    },
    "parent_roles": {
        "helper": "Помощник",
        "active_participant": "Активный участник",
        "audience": "Зритель",
        "evaluator": "Оценщик",
    },
    "parent_audience_engagement": {
        "none": "Без дополнительного участия",
        "feedback": "Обратная связь",
        "vote": "Голосование",
        "audience_award": "Приз зрительских симпатий",
    },
    "room": {
        "classroom": "Класс",
        "assembly_hall": "Актовый зал",
        "gym": "Спортивный зал",
        "other": "Другое помещение",
    },
    "style": {
        "classic": "Классический",
        "interactive": "Интерактивный",
        "creative": "Творческий",
        "research": "Исследовательский",
    },
    "script_detail": {
        "brief": "Краткий",
        "standard": "Стандартный",
        "detailed": "Подробный",
    },
    "difficulty": {
        "basic": "Базовая",
        "standard": "Стандартная",
        "advanced": "Повышенная",
    },
    "interaction_level": {
        "low": "Низкая",
        "medium": "Средняя",
        "high": "Высокая",
    },
    "preparation_effort": {
        "minimal": "Минимальная",
        "standard": "Стандартная",
        "extended": "Расширенная",
    },
}


def choices(field, values):
    labels = LABELS[field]
    return [{"value": value, "label": labels[value]} for value in values]


@router.get("/options")
def get_catalog_options():
    preference_fields = (
        "style",
        "script_detail",
        "difficulty",
        "interaction_level",
        "preparation_effort",
    )

    return {
        "regions": [
            {"value": "RU-SVE", "label": "Свердловская область"}
        ],
        "grade_groups": choices("grade_group", get_args(GradeGroup)),
        "grades": list(range(1, 12)),
        "pupils_count": {"min": 1, "max": 35},
        "duration_minutes": [
            {"value": value, "label": f"{value} минут"}
            for value in get_args(
                GenerationRequest.model_fields["duration_minutes"].annotation
            )
        ],
        "formats": choices("format", get_args(EventFormat)),
        "parent_roles": choices("parent_roles", get_args(ParentRole)),
        "parent_audience_engagement": choices(
            "parent_audience_engagement", get_args(AudienceEngagement)
        ),
        "rooms": choices("room", get_args(RoomType)),
        "teacher_preferences": {
            field: choices(
                field,
                get_args(TeacherPreferences.model_fields[field].annotation),
            )
            for field in preference_fields
        },
        "generation": {
            "variants_count": [1, 2, 3],
            "languages": [{"value": "ru", "label": "Русский"}],
        },
    }

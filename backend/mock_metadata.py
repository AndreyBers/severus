from datetime import datetime, timezone

from backend.catalog import list_events
from backend.schemas import GenerationRequest


def build_mock_variant_metadata(
    request: GenerationRequest,
    materials: list[dict],
) -> dict:
    instructions = [
        "Проверить и адаптировать тестовый сценарий перед использованием.",
        "Подготовить материалы: " + ", ".join(
            material["title"] for material in materials
        ),
        "Проверить оборудование и распределение ролей.",
    ]

    if request.participants.parents_enabled:
        instructions.append(
            "Согласовать участие родителей и запасной план."
        )

    return {
        "teacher_instructions": instructions,
        "sources": [],
        "quality_report": {
            "status": "warning",
            "issues": [
                {
                    "code": "MOCK_NOT_VALIDATED",
                    "severity": "warning",
                    "message": (
                        "Сценарий создан mock-генератором. "
                        "Педагогическая и культурная модерация не выполнялась."
                    ),
                }
            ],
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    }


def build_mock_generation_meta(request: GenerationRequest) -> dict:
    event = next(
        (e for e in list_events() if e.id == request.event_id),
        None,
    )

    return {
        "model_key": "mock",
        "prompt_version": "mock-0.1",
        "catalog_version": (
            event.catalog_version if event else "unknown"
        ),
    }

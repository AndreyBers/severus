from backend.schemas import GenerationRequest


def build_mock_project(
    request: GenerationRequest,
    job_id: str,
    project_id: str,
    event_title: str,
) -> dict:
    """Создаёт тестовый сценарий без LLM."""

    variants = []

    for index in range(request.generation.variants_count):
        duration = request.duration_minutes

        variants.append({
            "variant_id": f"v{index + 1}",
            "revision": 1,
            "status": "completed",
            "title": f"{event_title} — вариант {index + 1} (тест)",
            "timeline": [
                {"title": "Вступление", "start_minute": 0, "duration_minutes": 5},
                {"title": "Основная часть", "start_minute": 5, "duration_minutes": duration - 10},
                {"title": "Итоги", "start_minute": duration - 5, "duration_minutes": 5},
            ],
            "quality_report": {
                "status": "warning",
                "message": "Тестовый сценарий, не проверен",
            },
        })

    return {
        "schema_version": "1.2",
        "job_id": job_id,
        "project_id": project_id,
        "status": "completed",
        "requested_variants": request.generation.variants_count,
        "completed_variants": len(variants),
        "input": request.model_dump(mode="json"),
        "variants": variants,
    }

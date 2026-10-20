from backend.schemas import GenerationRequest
from backend.mock_concepts import MOCK_CONCEPTS
from backend.mock_roles import build_mock_roles
from backend.mock_timeline import build_mock_timeline
from backend.mock_materials import build_mock_materials
from backend.mock_parent_plan import build_mock_parent_plan
from backend.mock_metadata import (
    build_mock_variant_metadata,
    build_mock_generation_meta,
)


def build_mock_project(
    request: GenerationRequest,
    job_id: str,
    project_id: str,
    event_title: str,
) -> dict:
    """Создаёт тестовый сценарий без LLM."""

    variants = []

    for index in range(request.generation.variants_count):
        concept = MOCK_CONCEPTS[index]
        roles = build_mock_roles(request)
        timeline = build_mock_timeline(request, concept, roles)
        materials = build_mock_materials(concept)
        for material in materials:
            for block in timeline:
                if block['block_id'] in material['used_in_blocks']:
                    block['material_ids'].append(material['material_id'])

        parent_plan = build_mock_parent_plan(
            request, roles, timeline, materials
        )

        variants.append({
            "variant_id": f"v{index + 1}",
            "revision": 1,
            "status": "completed",
            "title": f"{event_title} — {concept['name']} (тест)",
            "concept": {
                "summary": f"Тестовый сценарий: {concept['name']}.",
                "goal": concept["goal"],
                "tasks": [concept["activity"]],
                "expected_outcomes": [concept["outcome"]],
            },
            "roles": roles,
            **({"parent_participation_plan": parent_plan} if parent_plan else {}),
            "timeline": timeline,
            "materials": materials,
            **build_mock_variant_metadata(request, materials),
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
        "generation_meta": build_mock_generation_meta(request),
    }

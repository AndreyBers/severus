from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def create_project(payload):
    response = client.post("/api/v1/generations", json=payload)
    assert response.status_code == 202

    accepted = response.json()
    result = client.get(accepted["project_url"])
    assert result.status_code == 200

    return result.json()


def test_full_project_contract():
    project = create_project({
        "event_id": "knowledge_day",
        "region_id": "RU-SVE",
        "grade": 6,
        "pupils_count": 25,
        "duration_minutes": 45,
        "format": "class_hour",
        "participants": {
            "parents_enabled": True,
            "parents_count": 12,
            "parent_roles": ["helper", "audience"],
            "parent_audience_engagement": "audience_award",
        },
        "generation": {"variants_count": 3},
    })

    assert project["schema_version"] == "1.2"
    assert project["status"] == "completed"
    assert project["requested_variants"] == 3
    assert project["completed_variants"] == 3
    assert len(project["variants"]) == 3

    assert set(project["generation_meta"]) >= {
        "model_key", "prompt_version", "catalog_version"
    }

    variant_ids = set()

    for variant in project["variants"]:
        assert set(variant) >= {
            "variant_id", "revision", "status", "title",
            "concept", "roles", "timeline", "materials",
            "parent_participation_plan", "teacher_instructions",
            "sources", "quality_report",
        }

        assert variant["status"] == "completed"
        assert variant["revision"] >= 1
        variant_ids.add(variant["variant_id"])

        assert set(variant["concept"]) >= {
            "summary", "goal", "tasks", "expected_outcomes"
        }

        blocks = variant["timeline"]
        roles = variant["roles"]
        materials = variant["materials"]

        block_ids = {b["block_id"] for b in blocks}
        role_ids = {r["role_id"] for r in roles}
        material_ids = {m["material_id"] for m in materials}

        assert len(block_ids) == len(blocks)
        assert len(role_ids) == len(roles)
        assert len(material_ids) == len(materials)

        assert blocks[0]["start_minute"] == 0
        assert sum(b["duration_minutes"] for b in blocks) == 45

        for block in blocks:
            assert set(block["role_ids"]) <= role_ids
            assert set(block["material_ids"]) <= material_ids

        for role in roles:
            assert set(role["block_ids"]) <= block_ids

        for material in materials:
            assert set(material["used_in_blocks"]) <= block_ids

        plan = variant["parent_participation_plan"]
        assert plan["parents_count"] == 12
        assert sum(a["count"] for a in plan["assignments"]) == 12
        assert plan["voting"]["enabled"] is True

        assert variant["quality_report"]["status"] == "warning"
        assert variant["quality_report"]["issues"]

    assert len(variant_ids) == 3


def test_normalized_defaults_contract():
    project = create_project({
        "event_id": "knowledge_day",
        "region_id": "RU-SVE",
        "grade": 6,
        "pupils_count": 25,
        "duration_minutes": 45,
        "format": "class_hour",
    })

    data = project["input"]

    assert data["grade_group"] == "5-8"
    assert data["participants"]["parents_count"] == 0
    assert data["resources"]["projector"] is None
    assert data["teacher_preferences"]["interaction_level"] == "low"
    assert data["teacher_preferences"]["group_work"] is False
    assert data["generation"]["variants_count"] == 1
    assert len(project["variants"]) == 1

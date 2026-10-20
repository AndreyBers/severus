from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


VALID_REQUEST = {
    "event_id": "knowledge_day",
    "region_id": "RU-SVE",
    "grade": 6,
    "pupils_count": 25,
    "duration_minutes": 45,
    "format": "class_hour",
    "generation": {
        "variants_count": 2,
        "language": "ru",
    },
}


def test_create_generation():
    response = client.post(
        "/api/v1/generations",
        json=VALID_REQUEST,
    )

    assert response.status_code == 202

    data = response.json()

    assert data["status"] == "queued"
    assert data["requested_variants"] == 2
    assert data["completed_variants"] == 0
    assert data["job_id"].startswith("job_")
    assert data["project_id"].startswith("evt_")


def test_unknown_event():
    request = {
        **VALID_REQUEST,
        "event_id": "unknown_event",
    }

    response = client.post(
        "/api/v1/generations",
        json=request,
    )

    assert response.status_code == 422


def test_invalid_generation_parameters():
    request = {
        **VALID_REQUEST,
        "pupils_count": 0,
    }

    response = client.post(
        "/api/v1/generations",
        json=request,
    )

    assert response.status_code == 422


def test_full_generation_flow():
    response = client.post(
        "/api/v1/generations",
        json=VALID_REQUEST,
    )

    assert response.status_code == 202
    accepted = response.json()

    status_response = client.get(accepted["status_url"])
    project_response = client.get(accepted["project_url"])

    assert status_response.status_code == 200
    assert project_response.status_code == 200

    job = status_response.json()
    project = project_response.json()

    assert job["status"] == "completed"
    assert job["completed_variants"] == 2
    assert project["completed_variants"] == 2
    assert len(project["variants"]) == 2
    assert project["input"]["grade_group"] == "5-8"

    for variant in project["variants"]:
        total = sum(
            block["duration_minutes"]
            for block in variant["timeline"]
        )
        assert total == 45


def test_missing_job_and_project():
    job_response = client.get(
        "/api/v1/generations/job_missing"
    )
    project_response = client.get(
        "/api/v1/projects/evt_missing"
    )

    assert job_response.status_code == 404
    assert project_response.status_code == 404


def test_three_distinct_mock_concepts():
    request = {
        **VALID_REQUEST,
        "generation": {"variants_count": 3, "language": "ru"},
    }

    response = client.post("/api/v1/generations", json=request)
    assert response.status_code == 202

    project_response = client.get(response.json()["project_url"])
    assert project_response.status_code == 200

    variants = project_response.json()["variants"]
    assert len(variants) == 3

    goals = [v["concept"]["goal"] for v in variants]
    activities = [v["timeline"][1]["title"] for v in variants]

    assert len(set(goals)) == 3
    assert len(set(activities)) == 3

    for variant in variants:
        assert variant["concept"]["tasks"][0] == variant["timeline"][1]["title"]


def test_mock_roles_match_request():
    request = {
        **VALID_REQUEST,
        "participants": {"teachers_count": 2},
    }

    response = client.post("/api/v1/generations", json=request)
    assert response.status_code == 202

    project = client.get(response.json()["project_url"]).json()
    variant = project["variants"][0]

    roles = variant["roles"]
    teachers = [r for r in roles if r["participant_type"] == "teacher"]
    pupils = [r for r in roles if r["participant_type"] == "pupils_group"]

    assert len(teachers) == 2
    assert len(pupils) == 1
    assert pupils[0]["count"] == 25

    block_ids = {b["block_id"] for b in variant["timeline"]}
    for role in roles:
        assert set(role["block_ids"]) <= block_ids


def test_mock_parent_roles():
    request = {
        **VALID_REQUEST,
        "participants": {
            "teachers_count": 2,
            "parents_enabled": True,
            "parents_count": 12,
            "parent_roles": ["helper", "audience"],
        },
    }

    response = client.post("/api/v1/generations", json=request)
    assert response.status_code == 202

    project = client.get(response.json()["project_url"]).json()
    roles = project["variants"][0]["roles"]
    parents = [r for r in roles if r["participant_type"] == "parent"]

    assert len(parents) == 2
    assert sum(r["count"] for r in parents) == 12
    assert {r["role_mode"] for r in parents} == {"helper", "audience"}


def test_mock_without_parents():
    response = client.post("/api/v1/generations", json=VALID_REQUEST)
    assert response.status_code == 202

    project = client.get(response.json()["project_url"]).json()
    roles = project["variants"][0]["roles"]

    assert not any(r["participant_type"] == "parent" for r in roles)


def test_detailed_timeline_contract():
    response = client.post(
        "/api/v1/generations",
        json=VALID_REQUEST,
    )

    assert response.status_code == 202

    project = client.get(
        response.json()["project_url"]
    ).json()

    variant = project["variants"][0]
    blocks = variant["timeline"]
    roles = variant["roles"]

    required_fields = {
        "block_id",
        "start_minute",
        "duration_minutes",
        "title",
        "purpose",
        "teacher_script",
        "pupil_actions",
        "role_ids",
        "material_ids",
    }

    assert blocks[0]["start_minute"] == 0
    assert sum(b["duration_minutes"] for b in blocks) == 45

    role_ids = {r["role_id"] for r in roles}

    for index, block in enumerate(blocks):
        assert required_fields <= block.keys()
        assert block["teacher_script"]
        assert block["pupil_actions"]
        assert set(block["role_ids"]) <= role_ids

        if index > 0:
            previous = blocks[index - 1]
            assert block["start_minute"] == (
                previous["start_minute"]
                + previous["duration_minutes"]
            )

    for role in roles:
        for block in blocks:
            if block["block_id"] in role["block_ids"]:
                assert role["role_id"] in block["role_ids"]


def test_mock_materials_contract():
    response = client.post(
        "/api/v1/generations",
        json=VALID_REQUEST,
    )
    assert response.status_code == 202

    result = client.get(response.json()["project_url"])
    assert result.status_code == 200

    for variant in result.json()["variants"]:
        blocks = variant["timeline"]
        materials = variant["materials"]

        block_ids = {b["block_id"] for b in blocks}
        material_ids = {m["material_id"] for m in materials}

        assert len(materials) == 2
        assert len(material_ids) == len(materials)

        for material in materials:
            assert material["used_in_blocks"]
            assert material["content"]
            assert material["print_required"] is False
            assert set(material["used_in_blocks"]) <= block_ids

            for block in blocks:
                if block["block_id"] in material["used_in_blocks"]:
                    assert material["material_id"] in block["material_ids"]

        for block in blocks:
            assert set(block["material_ids"]) <= material_ids


def test_parent_plan_with_audience_award():
    request = {
        **VALID_REQUEST,
        "participants": {
            "parents_enabled": True,
            "parents_count": 12,
            "parent_roles": ["helper", "audience"],
            "parent_audience_engagement": "audience_award",
        },
        "resources": {"printer": False},
    }

    response = client.post("/api/v1/generations", json=request)
    assert response.status_code == 202

    project = client.get(response.json()["project_url"]).json()

    for variant in project["variants"]:
        plan = variant["parent_participation_plan"]
        assert plan["parents_count"] == 12
        assert plan["parent_size_group"] == "11_plus"
        assert sum(a["count"] for a in plan["assignments"]) == 12

        voting = plan["voting"]
        assert voting["voters_count_planned"] == 10
        assert voting["method"] == "show_of_hands"

        role_ids = {r["role_id"] for r in variant["roles"]}
        material_ids = {m["material_id"] for m in variant["materials"]}

        assert all(a["role_id"] in role_ids for a in plan["assignments"])
        assert set(voting["material_ids"]) <= material_ids
        assert voting["block_id"] in {
            b["block_id"] for b in variant["timeline"]
        }


def test_parent_plan_without_parents():
    response = client.post("/api/v1/generations", json=VALID_REQUEST)
    project = client.get(response.json()["project_url"]).json()

    for variant in project["variants"]:
        assert "parent_participation_plan" not in variant


def test_parent_feedback_without_voting():
    request = {
        **VALID_REQUEST,
        "participants": {
            "parents_enabled": True,
            "parents_count": 3,
            "parent_roles": ["audience"],
            "parent_audience_engagement": "feedback",
        },
    }

    response = client.post("/api/v1/generations", json=request)
    project = client.get(response.json()["project_url"]).json()
    plan = project["variants"][0]["parent_participation_plan"]

    assert plan["parent_size_group"] == "3-5"
    assert plan["voting"] is None
    assert plan["assignments"][0]["count"] == 3


def test_mock_quality_report_and_instructions():
    response = client.post(
        "/api/v1/generations",
        json=VALID_REQUEST,
    )
    assert response.status_code == 202

    project_response = client.get(response.json()["project_url"])
    assert project_response.status_code == 200

    for variant in project_response.json()["variants"]:
        assert variant["teacher_instructions"]
        assert variant["sources"] == []

        report = variant["quality_report"]
        assert report["status"] == "warning"
        assert report["checked_at"]
        assert any(
            issue["code"] == "MOCK_NOT_VALIDATED"
            for issue in report["issues"]
        )


def test_mock_generation_metadata():
    response = client.post(
        "/api/v1/generations",
        json=VALID_REQUEST,
    )
    assert response.status_code == 202

    project = client.get(response.json()["project_url"]).json()

    assert project["schema_version"] == "1.2"

    metadata = project["generation_meta"]
    assert metadata["model_key"] == "mock"
    assert metadata["prompt_version"] == "mock-0.1"
    assert metadata["catalog_version"] != "unknown"

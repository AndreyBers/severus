from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from backend.catalog import list_events
from backend.schemas import GenerationRequest


router = APIRouter(
    prefix="/api/v1",
    tags=["Generations"],
)

# Временное хранилище заданий для Sprint 1.
# Позже заменим постоянным хранилищем.
jobs = {}
projects = {}


class GenerationAccepted(BaseModel):
    job_id: str
    project_id: str
    status: str
    requested_variants: int
    completed_variants: int
    status_url: str
    project_url: str


@router.post(
    "/generations",
    response_model=GenerationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_generation(request: GenerationRequest, background_tasks: BackgroundTasks):
    events = {
        event.id: event
        for event in list_events()
    }

    event = events.get(request.event_id)

    if event is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "EVENT_NOT_FOUND",
                "message": "Неизвестное мероприятие",
                "field": "event_id",
            },
        )

    if request.grade_group not in event.supported_age_groups:
        raise HTTPException(
            status_code=422,
            detail="Возрастная группа не поддерживается",
        )

    if request.format not in event.supported_formats:
        raise HTTPException(
            status_code=422,
            detail="Формат мероприятия не поддерживается",
        )

    job_id = f"job_{uuid4().hex}"
    project_id = f"evt_{uuid4().hex}"

    jobs[job_id] = {
        "job_id": job_id,
        "project_id": project_id,
        "status": "queued",
        "requested_variants": request.generation.variants_count,
        "completed_variants": 0,
        "input": request.model_dump(mode="json"),
    }

    background_tasks.add_task(
        finish_mock_generation, job_id, request, event.title
    )

    return GenerationAccepted(
        job_id=job_id,
        project_id=project_id,
        status="queued",
        requested_variants=request.generation.variants_count,
        completed_variants=0,
        status_url=f"/api/v1/generations/{job_id}",
        project_url=f"/api/v1/projects/{project_id}",
    )


def finish_mock_generation(
    job_id: str,
    request: GenerationRequest,
    event_title: str,
) -> None:
    from backend.mock_generator import build_mock_project

    job = jobs[job_id]
    job["status"] = "running"

    try:
        result = build_mock_project(
            request, job_id, job["project_id"], event_title
        )
        projects[job["project_id"]] = result
        job["completed_variants"] = len(result["variants"])
        job["status"] = "completed"
    except Exception:
        job["status"] = "failed"
        raise


@router.get("/generations/{job_id}")
def get_generation(job_id: str):
    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Задание не найдено",
        )

    completed = job["completed_variants"]

    return {
        "job_id": job_id,
        "project_id": job["project_id"],
        "status": job["status"],
        "phase": job["status"],
        "requested_variants": job["requested_variants"],
        "completed_variants": completed,
        "variants": [
            {
                "variant_id": f"v{i}",
                "status": "completed" if i <= completed else job["status"],
                "revision": 1,
            }
            for i in range(1, job["requested_variants"] + 1)
        ],
        "warnings": [],
        "errors": [],
    }


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    project = projects.get(project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Готовый проект не найден",
        )

    return project

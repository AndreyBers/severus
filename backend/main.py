from backend.errors import register_error_handlers
from fastapi import FastAPI

from backend.catalog import router as catalog_router
from backend.generations import router as generations_router
from backend.catalog_options import router as catalog_options_router


app = FastAPI(
    title="Северус API",
    description="Backend ИИ-сервиса школьных событий",
    version="0.1.0",
)

app.include_router(catalog_router)
app.include_router(generations_router)
app.include_router(catalog_options_router)
register_error_handlers(app)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "severus-backend",
    }

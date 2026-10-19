from fastapi import FastAPI

app = FastAPI(
    title="Северус API",
    description="Backend ИИ-сервиса школьных событий",
    version="0.1.0",
)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "severus-backend",
    }

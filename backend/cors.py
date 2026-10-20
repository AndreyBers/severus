import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def configure_cors(app: FastAPI) -> None:
    raw = os.getenv("SEVERUS_CORS_ORIGINS")

    origins = (
        [item.strip() for item in raw.split(",") if item.strip()]
        if raw
        else DEFAULT_ORIGINS
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

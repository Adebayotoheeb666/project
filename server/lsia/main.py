from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from lsia.api.routes import router
from lsia.application.errors import AppError
from lsia.config import settings
from lsia.infrastructure import db, models  # noqa: F401
from lsia.infrastructure.crypto import load_or_create_identity


def create_app() -> FastAPI:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db.Base.metadata.create_all(bind=db.engine)

    app = FastAPI(title="LSIA School Computer", version="0.1.0")
    app.state.identity = load_or_create_identity()

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if origins == ["*"] else origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    app.include_router(router)

    candidates = [
        Path(__file__).resolve().parents[2] / "admin" / "dist",
        Path(__file__).resolve().parents[1] / "admin" / "dist",
        Path(__file__).resolve().parent / "dist",
    ]
    admin_dist = next((c for c in candidates if c.exists()), candidates[0])
    if admin_dist.exists():
        app.mount("/", StaticFiles(directory=admin_dist, html=True), name="admin")

    return app

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, documents
from app.config import get_settings
from app.db.session import Base, engine
from app.schemas import HealthResponse
from app.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(chat.router)

    @app.on_event("startup")
    def on_startup():
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(bind=engine)
        logger.info("%s started", settings.app_name)

    @app.get("/health", response_model=HealthResponse)
    def health():
        db_status = "ok"
        chroma_status = "ok"
        embedding_status = "all-MiniLM-L6-v2"
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
        except Exception as exc:
            db_status = f"error: {exc}"

        try:
            from app.services.chroma_service import get_chroma_service

            chroma_status = get_chroma_service().health()
        except Exception as exc:
            chroma_status = f"error: {exc}"

        overall = "ok" if db_status == "ok" else "degraded"
        return HealthResponse(
            status=overall,
            database=db_status,
            chroma=chroma_status,
            embedding_model=embedding_status,
        )

    return app


app = create_app()

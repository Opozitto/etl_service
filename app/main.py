from fastapi import FastAPI

from app.api.routes.documents import router as documents_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Автономный ETL-микросервис для структурирования документов",
    )
    app.include_router(documents_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

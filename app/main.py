from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import owner, public


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="SoukSaaS", lifespan=lifespan)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(public.router)
    application.include_router(owner.router)
    return application


app = create_app()

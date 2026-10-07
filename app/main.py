from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import DEFAULT_DB_PATH, init_db
from app.routers import (
    associations,
    calculations,
    criteria,
    evaluations,
    listings,
    neighborhoods,
    tips,
    ui,
)

ROOT = Path(__file__).resolve().parent.parent


def create_app(db_path: str | Path = DEFAULT_DB_PATH, seed: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(db_path, seed=seed)
        yield

    app = FastAPI(
        title="Apartment Buying Assistant",
        description="Local-first API for evaluating Swedish bostadsrätter, BRFs and monthly costs.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.db_path = str(db_path)

    for module in (tips, criteria, neighborhoods, associations, listings, evaluations, calculations, ui):
        app.include_router(module.router)

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()

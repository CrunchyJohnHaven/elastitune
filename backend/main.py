from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .services.persistence_service import PersistenceService
from .services.run_manager import RunManager
from .api import routes_health, routes_connect, routes_runs, routes_committee, ws_runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create shared state on startup."""
    persistence = PersistenceService()
    await persistence.init()
    app.state.run_manager = RunManager(persistence=persistence)
    yield
    # Cleanup: cancel any running tasks on shutdown
    run_manager: RunManager = app.state.run_manager
    for run_id, ctx in run_manager.runs.items():
        ctx.cancel_flag.set()
        for task in ctx.tasks:
            task.cancel()
    for run_id, ctx in run_manager.committee_runs.items():
        ctx.cancel_flag.set()
        for task in ctx.tasks:
            task.cancel()


app = FastAPI(
    title="ElastiTune",
    version="0.1.0",
    description="Autonomous Elasticsearch search profile optimisation with live visualisation.",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(routes_health.router, prefix="/api")
app.include_router(routes_connect.router, prefix="/api")
app.include_router(routes_runs.router, prefix="/api")
app.include_router(routes_committee.router, prefix="/api")
app.include_router(ws_runs.router)  # WebSocket — no /api prefix

# ---------------------------------------------------------------------------
# Static files (production frontend)
# ---------------------------------------------------------------------------

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/", include_in_schema=False)
    async def spa_index():
        return FileResponse(frontend_dist / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        candidate = frontend_dist / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")

# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )

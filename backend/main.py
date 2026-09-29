"""FastAPI application entrypoint for AsyncApply: mounts routers."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import asyncapply, asyncapply_admin, asyncapply_config, leads
from services.asyncapply.worker import recover_orphaned_work

load_dotenv()

DEV_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]


def _allowed_origins() -> list[str]:
    """Resolve the CORS allowlist for this deployment.

    Defaults to the local dev ports; set CORS_ORIGINS to a comma-separated
    list of real origins in production. Deliberately never "*", since the
    API is credentialed.

    Returns:
        The origins permitted to call this API from a browser.
    """
    configured = os.getenv("CORS_ORIGINS", "").strip()
    if not configured:
        return DEV_ORIGINS
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(title="AsyncApply")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(asyncapply.router, prefix="/api/v1")
app.include_router(asyncapply_config.router, prefix="/api/v1")
app.include_router(asyncapply_admin.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")


@app.on_event("startup")
def on_startup() -> None:
    """Recover any work interrupted by a server restart.

    The schema itself is owned by Alembic: run `uv run alembic upgrade head`
    before starting the app (the Docker image does this automatically).
    """
    recover_orphaned_work()


@app.get("/health")
def health_check() -> dict[str, str]:
    """Simple liveness check.

    Returns:
        dict[str, str]: A static ok status.
    """
    return {"status": "ok"}

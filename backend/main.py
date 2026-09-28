"""FastAPI application entrypoint for AsyncApply: mounts routers."""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import asyncapply, asyncapply_admin, asyncapply_config
from services.asyncapply.worker import recover_orphaned_work

load_dotenv()

app = FastAPI(title="AsyncApply")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(asyncapply.router, prefix="/api/v1")
app.include_router(asyncapply_config.router, prefix="/api/v1")
app.include_router(asyncapply_admin.router, prefix="/api/v1")


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

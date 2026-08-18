"""FastAPI backend for Outreach OS.

Serves the API and the built React SPA in production.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api import dashboard, leads, offers, runs, signals, settings as settings_mod

app = FastAPI(title="Outreach OS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(offers.router, prefix="/api")
app.include_router(settings_mod.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    store_ok, store_error = True, None
    try:
        from src.db.queries import ping
        ping()
    except Exception as exc:
        store_ok, store_error = False, f"{type(exc).__name__}: {exc}"
    return {"status": "ok", "store_reachable": store_ok, "store_error": store_error}


_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


def mount_console(application: FastAPI = app) -> bool:
    if not _DIST.is_dir():
        return False

    application.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @application.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Unknown API route")
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")

    return True


CONSOLE_MOUNTED = mount_console()
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import router
from app.core.config import ROOT, settings

app = FastAPI(
    title="MoneyPrinterTurbo NoAPI",
    version=__version__,
    description="Local-first AI short-video studio with account-based providers and no user API keys.",
)
app.include_router(router)

web_dir = ROOT / "web"
assets_dir = web_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(web_dir / "index.html")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    candidate = (web_dir / path).resolve()
    if candidate.is_file() and web_dir in candidate.parents:
        return FileResponse(candidate)
    return FileResponse(web_dir / "index.html")


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()

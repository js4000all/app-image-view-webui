from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import create_api_router
from app.config import AppSettings
from app.repositories.filesystem import FileSystemRepository
from app.services.image_service import ImageService, ResourceRegistry

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(settings: AppSettings) -> FastAPI:
    app = FastAPI(title="app-image-view-webui")
    repository = FileSystemRepository()
    registry = ResourceRegistry()
    service = ImageService(base_dir=settings.base_dir, repository=repository, registry=registry)

    app.include_router(create_api_router(service))

    @app.get("/")
    def home() -> FileResponse:
        return FileResponse(settings.static_dir / "home-app" / "index.html")

    @app.get("/viewer")
    def viewer() -> FileResponse:
        return FileResponse(settings.static_dir / "viewer.html")

    app.mount("/", StaticFiles(directory=str(settings.static_dir), html=False), name="static")
    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Image viewer web UI")
    parser.add_argument("image_dir", type=Path, help="Directory containing image subdirectories")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--static-dir", type=Path, default=DEFAULT_STATIC_DIR, help="Directory containing static files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = AppSettings.from_paths(base_dir=args.image_dir, static_dir=args.static_dir)

    if not settings.base_dir.exists() or not settings.base_dir.is_dir():
        raise SystemExit(f"Directory does not exist: {settings.base_dir}")
    if not settings.static_dir.exists() or not settings.static_dir.is_dir():
        raise SystemExit(f"Static directory does not exist: {settings.static_dir}")

    app = create_app(settings)
    print(f"Serving {settings.base_dir} on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

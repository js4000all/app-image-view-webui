from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import create_api_router
from app.config import AppSettings, load_root_presets
from app.repositories.filesystem import FileSystemRepository
from app.services.image_service import ImageService, ResourceRegistry
from app.services.tag_index_service import TagIndexService

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
DEFAULT_PRESETS_FILE = Path("root-presets.yaml")


def create_app(settings: AppSettings) -> FastAPI:
    app = FastAPI(title="app-image-view-webui")
    repository = FileSystemRepository()
    registry = ResourceRegistry(roots=settings.roots)
    service = ImageService(roots=settings.roots, repository=repository, registry=registry)
    tag_index_service = TagIndexService(roots=settings.roots, repository=repository, registry=registry, db_path=settings.db_path)

    loaded_count = 0
    load_failed = False
    try:
        loaded_count = tag_index_service.load_index_from_db(reconcile_directories=False)
    except sqlite3.Error:
        load_failed = True

    fallback_built = load_failed or loaded_count == 0
    if fallback_built:
        tag_index_service.build_index()

    print(f"[tag-index] startup load_count={loaded_count} fallback_build={fallback_built} db={settings.db_path.name}")

    app.include_router(create_api_router(service, tag_index_service))

    @app.get("/")
    def home() -> FileResponse:
        return FileResponse(settings.static_dir / "home-app" / "index.html")

    @app.get("/viewer")
    def viewer() -> FileResponse:
        return FileResponse(settings.static_dir / "home-app" / "index.html")

    app.mount("/", StaticFiles(directory=str(settings.static_dir), html=False), name="static")
    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Image viewer web UI")
    parser.add_argument("target", type=str, help="Preset key or directory path")
    parser.add_argument("--presets-file", type=Path, default=DEFAULT_PRESETS_FILE, help="YAML file containing presets")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--static-dir", type=Path, default=DEFAULT_STATIC_DIR, help="Directory containing static files")
    return parser.parse_args()


def resolve_settings(args: argparse.Namespace) -> AppSettings:
    target_path = Path(args.target).expanduser()
    if target_path.exists() and target_path.is_dir():
        return AppSettings.from_paths(base_dir=target_path, static_dir=args.static_dir)

    presets_file = args.presets_file.expanduser().resolve()
    if not presets_file.exists():
        raise SystemExit(f"Presets file does not exist: {presets_file}")

    presets = load_root_presets(presets_file)
    if args.target not in presets:
        available = ", ".join(sorted(presets)) or "<none>"
        raise SystemExit(f"Unknown preset key: {args.target}. Available presets: {available}")

    return AppSettings.from_preset(preset_key=args.target, roots=presets[args.target], static_dir=args.static_dir)


def main() -> None:
    args = parse_args()
    settings = resolve_settings(args)

    for root_key, root_path in settings.roots.items():
        if not root_path.exists() or not root_path.is_dir():
            raise SystemExit(f"Root directory does not exist ({root_key}): {root_path}")
    if not settings.static_dir.exists() or not settings.static_dir.is_dir():
        raise SystemExit(f"Static directory does not exist: {settings.static_dir}")

    app = create_app(settings)
    roots_summary = ", ".join(f"{key}={path}" for key, path in settings.roots.items())
    print(f"Serving preset={settings.preset_key} roots[{roots_summary}] on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

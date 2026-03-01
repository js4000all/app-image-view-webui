from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import AppSettings
from app.main import DEFAULT_STATIC_DIR, create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI spec as JSON")
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("tests/resources/image_root"),
        help="Existing image root path used to initialize app services",
    )
    parser.add_argument(
        "--static-dir",
        type=Path,
        default=DEFAULT_STATIC_DIR,
        help="Static directory path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("frontend/openapi/openapi.json"),
        help="Output file path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = AppSettings.from_paths(base_dir=args.image_dir, static_dir=args.static_dir)
    app = create_app(settings)
    openapi_schema = app.openapi()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(openapi_schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote OpenAPI spec to {args.output}")


if __name__ == "__main__":
    main()

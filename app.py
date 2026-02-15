#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import threading
from uuid import uuid4
from email.utils import formatdate, parsedate_to_datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
STATIC_DIR = Path(__file__).parent / "static"


class ImageViewHandler(SimpleHTTPRequestHandler):
    base_dir: Path
    _id_to_path: dict[str, Path] = {}
    _path_to_id: dict[Path, str] = {}
    _resource_lock = threading.Lock()

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _safe_path(self, raw_path: str) -> Path:
        target = (self.base_dir / unquote(raw_path)).resolve()
        if not target.is_relative_to(self.base_dir):
            raise PermissionError("path traversal detected")
        return target

    def _read_json_body(self) -> dict:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("missing Content-Length")

        try:
            body_size = int(content_length)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc

        if body_size <= 0:
            raise ValueError("empty body")

        try:
            raw_body = self.rfile.read(body_size)
            payload = json.loads(raw_body.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid json") from exc

        if not isinstance(payload, dict):
            raise ValueError("json must be object")

        return payload

    def _register_resource_id(self, path: Path) -> str:
        resolved_path = path.resolve()
        with self._resource_lock:
            resource_id = self._path_to_id.get(resolved_path)
            if resource_id is None:
                resource_id = uuid4().hex
                self._path_to_id[resolved_path] = resource_id
                self._id_to_path[resource_id] = resolved_path
            return resource_id

    def _discard_resource_id(self, path: Path) -> None:
        resolved_path = path.resolve()
        with self._resource_lock:
            resource_id = self._path_to_id.pop(resolved_path, None)
            if resource_id is not None:
                self._id_to_path.pop(resource_id, None)

    def _resolve_resource_id(self, resource_id: str, *, expect_directory: bool) -> Path | None:
        with self._resource_lock:
            path = self._id_to_path.get(resource_id)

        if path is None:
            return None

        if not path.exists() or not path.is_relative_to(self.base_dir):
            self._discard_resource_id(path)
            return None

        if expect_directory and not path.is_dir():
            return None
        if not expect_directory and not path.is_file():
            return None

        return path

    def _image_entries(self, directory: Path) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        for entry in sorted(directory.iterdir()):
            if not entry.is_file() or entry.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            images.append({"file_id": self._register_resource_id(entry), "name": entry.name})
        return images

    def _subdirectory_entries(self) -> list[dict[str, str]]:
        subdirectories: list[dict[str, str]] = []
        for entry in sorted(self.base_dir.iterdir(), reverse=True):
            if not entry.is_dir():
                continue
            subdirectories.append({"directory_id": self._register_resource_id(entry), "name": entry.name})
        return subdirectories

    def _serve_image(self, send_body: bool) -> None:
        path = urlparse(self.path).path
        file_id = path.removeprefix("/api/image/")
        if not file_id:
            return self.send_error(HTTPStatus.NOT_FOUND)

        file_path = self._resolve_resource_id(file_id, expect_directory=False)
        if file_path is None:
            return self.send_error(HTTPStatus.NOT_FOUND)
        if not file_path.exists() or not file_path.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND)
        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            return self.send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

        try:
            stat_result = file_path.stat()
            content_length = stat_result.st_size
        except OSError:
            return self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)

        etag = f'W/"{stat_result.st_mtime_ns}-{stat_result.st_size}"'
        last_modified = formatdate(stat_result.st_mtime, usegmt=True)
        if_none_match = self.headers.get("If-None-Match")
        if_modified_since = self.headers.get("If-Modified-Since")

        if if_none_match and if_none_match.strip() == etag:
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header("ETag", etag)
            self.send_header("Last-Modified", last_modified)
            self.send_header("Cache-Control", "public, max-age=31536000")
            self.end_headers()
            return

        if if_modified_since:
            try:
                since_timestamp = parsedate_to_datetime(if_modified_since).timestamp()
                if stat_result.st_mtime <= since_timestamp:
                    self.send_response(HTTPStatus.NOT_MODIFIED)
                    self.send_header("ETag", etag)
                    self.send_header("Last-Modified", last_modified)
                    self.send_header("Cache-Control", "public, max-age=31536000")
                    self.end_headers()
                    return
            except (TypeError, ValueError, OverflowError):
                pass

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", last_modified)
        self.send_header("Cache-Control", "public, max-age=31536000")
        self.end_headers()

        if not send_body:
            return

        try:
            with file_path.open("rb") as f:
                self.copyfile(f, self.wfile)
        except OSError:
            return self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/subdirectories":
            return self._send_json({"subdirectories": self._subdirectory_entries()})

        if path.startswith("/api/images/"):
            directory_id = path.removeprefix("/api/images/")
            directory = self._resolve_resource_id(directory_id, expect_directory=True)
            if directory is None:
                return self.send_error(HTTPStatus.NOT_FOUND)

            return self._send_json(
                {
                    "directory_id": directory_id,
                    "subdirectory": directory.name,
                    "images": self._image_entries(directory),
                }
            )

        if path.startswith("/api/image/"):
            return self._serve_image(send_body=True)

        if path == "/":
            self.path = "/home.html"
        elif path == "/viewer":
            self.path = "/viewer.html"

        return super().do_GET()

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path.startswith("/api/image/"):
            return self._serve_image(send_body=False)
        return super().do_HEAD()

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/image/"):
            return self.send_error(HTTPStatus.NOT_FOUND)

        file_id = path.removeprefix("/api/image/")
        if not file_id:
            return self.send_error(HTTPStatus.NOT_FOUND)

        file_path = self._resolve_resource_id(file_id, expect_directory=False)
        if file_path is None:
            return self.send_error(HTTPStatus.NOT_FOUND)
        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            return self.send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        if not file_path.exists() or not file_path.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND)

        try:
            file_path.unlink()
        except OSError:
            return self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)

        self._discard_resource_id(file_path)

        return self._send_json({"deleted": file_path.name, "file_id": file_id}, status=HTTPStatus.OK)

    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/subdirectories/"):
            return self.send_error(HTTPStatus.NOT_FOUND)

        directory_id = path.removeprefix("/api/subdirectories/")
        if not directory_id:
            return self.send_error(HTTPStatus.NOT_FOUND)

        current_directory = self._resolve_resource_id(directory_id, expect_directory=True)
        if current_directory is None:
            return self.send_error(HTTPStatus.NOT_FOUND)

        try:
            payload = self._read_json_body()
        except ValueError:
            return self.send_error(HTTPStatus.BAD_REQUEST)

        new_name = payload.get("new_name")
        if not isinstance(new_name, str):
            return self.send_error(HTTPStatus.BAD_REQUEST)

        stripped_name = new_name.strip()
        if not stripped_name:
            return self.send_error(HTTPStatus.BAD_REQUEST)
        if stripped_name in {".", ".."}:
            return self.send_error(HTTPStatus.BAD_REQUEST)
        if re.search(r"[\\/]", stripped_name):
            return self.send_error(HTTPStatus.BAD_REQUEST)

        destination = self.base_dir / stripped_name
        if destination.exists():
            return self.send_error(HTTPStatus.CONFLICT)

        try:
            current_directory.rename(destination)
        except OSError:
            return self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)

        self._discard_resource_id(current_directory)
        new_directory_id = self._register_resource_id(destination)

        return self._send_json(
            {
                "directory_id": new_directory_id,
                "renamed_from": current_directory.name,
                "renamed_to": stripped_name,
            },
            status=HTTPStatus.OK,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Image viewer web UI")
    parser.add_argument("image_dir", type=Path, help="Directory containing image subdirectories")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = args.image_dir.expanduser().resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        raise SystemExit(f"Directory does not exist: {base_dir}")

    handler_class = type("ConfiguredImageViewHandler", (ImageViewHandler,), {"base_dir": base_dir})
    server = ThreadingHTTPServer((args.host, args.port), handler_class)
    print(f"Serving {base_dir} on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

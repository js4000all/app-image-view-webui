#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import re
from email.utils import formatdate, parsedate_to_datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
STATIC_DIR = Path(__file__).parent / "static"


class ImageViewHandler(SimpleHTTPRequestHandler):
    base_dir: Path

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

    def _image_entries(self, directory: Path) -> list[str]:
        return [
            entry.name
            for entry in sorted(directory.iterdir())
            if entry.is_file() and entry.suffix.lower() in IMAGE_EXTENSIONS
        ]

    def _subdirectory_entries(self) -> list[str]:
        return [entry.name for entry in sorted(self.base_dir.iterdir(), reverse=True) if entry.is_dir()]

    def _serve_image(self, send_body: bool) -> None:
        path = urlparse(self.path).path
        image_path = path.removeprefix("/api/image/")
        parts = image_path.split("/")
        if len(parts) < 2:
            return self.send_error(HTTPStatus.NOT_FOUND)

        subdir = "/".join(parts[:-1])
        filename = parts[-1]

        try:
            directory = self._safe_path(subdir)
            file_path = (directory / unquote(filename)).resolve()
        except PermissionError:
            return self.send_error(HTTPStatus.FORBIDDEN)

        if not file_path.is_relative_to(directory):
            return self.send_error(HTTPStatus.FORBIDDEN)
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
            subdir = path.removeprefix("/api/images/")
            try:
                directory = self._safe_path(subdir)
            except PermissionError:
                return self.send_error(HTTPStatus.FORBIDDEN)

            if not directory.exists() or not directory.is_dir():
                return self.send_error(HTTPStatus.NOT_FOUND)

            return self._send_json({"subdirectory": subdir, "images": self._image_entries(directory)})

        if path.startswith("/api/image/"):
            return self._serve_image(send_body=True)

        if path == "/":
            self.path = "/home.html"
        elif path == "/viewer":
            self.path = "/index.html"

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

        image_path = path.removeprefix("/api/image/")
        parts = image_path.split("/")
        if len(parts) < 2:
            return self.send_error(HTTPStatus.NOT_FOUND)

        subdir = "/".join(parts[:-1])
        filename = parts[-1]

        try:
            directory = self._safe_path(subdir)
            file_path = (directory / unquote(filename)).resolve()
        except PermissionError:
            return self.send_error(HTTPStatus.FORBIDDEN)

        if not file_path.is_relative_to(directory):
            return self.send_error(HTTPStatus.FORBIDDEN)
        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            return self.send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        if not file_path.exists() or not file_path.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND)

        try:
            file_path.unlink()
        except OSError:
            return self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)

        return self._send_json({"deleted": filename}, status=HTTPStatus.OK)

    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/subdirectories/"):
            return self.send_error(HTTPStatus.NOT_FOUND)

        current_name = path.removeprefix("/api/subdirectories/")
        if not current_name:
            return self.send_error(HTTPStatus.NOT_FOUND)

        try:
            current_directory = self._safe_path(current_name)
        except PermissionError:
            return self.send_error(HTTPStatus.FORBIDDEN)

        if not current_directory.exists() or not current_directory.is_dir():
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

        return self._send_json({"renamed_from": current_name, "renamed_to": stripped_name}, status=HTTPStatus.OK)


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

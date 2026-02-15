from __future__ import annotations

import shutil
import sys
import threading
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import ImageViewHandler
from http.server import ThreadingHTTPServer


@pytest.fixture
def copied_image_root(tmp_path: Path) -> Path:
    source = Path("tests/resources/image_root")
    destination = tmp_path / "image_root"
    shutil.copytree(source, destination)
    return destination


@pytest.fixture
def empty_image_root(tmp_path: Path) -> Path:
    destination = tmp_path / "empty_image_root"
    destination.mkdir()
    return destination


@pytest.fixture
def api_client_factory():
    clients: list[httpx.Client] = []
    servers: list[ThreadingHTTPServer] = []
    threads: list[threading.Thread] = []

    def _start(base_dir: Path) -> httpx.Client:
        handler_class = type(
            "ConfiguredImageViewHandler",
            (ImageViewHandler,),
            {
                "base_dir": base_dir,
                "_id_to_path": {},
                "_path_to_id": {},
                "_resource_lock": threading.Lock(),
            },
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        host, port = server.server_address
        client = httpx.Client(base_url=f"http://{host}:{port}")

        clients.append(client)
        servers.append(server)
        threads.append(thread)
        return client

    yield _start

    for client in clients:
        client.close()
    for server in servers:
        server.shutdown()
        server.server_close()
    for thread in threads:
        thread.join(timeout=2)

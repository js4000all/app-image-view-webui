from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import httpx
import pytest


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
def api_client_factory(free_tcp_port_factory):
    clients: list[httpx.Client] = []
    processes: list[subprocess.Popen] = []

    def _start(base_dir: Path) -> httpx.Client:
        port = free_tcp_port_factory()
        process = subprocess.Popen(
            [
                "python",
                "app.py",
                str(base_dir),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        base_url = f"http://127.0.0.1:{port}"
        client = httpx.Client(base_url=base_url, timeout=5.0)

        deadline = time.time() + 5
        last_error: Exception | None = None
        while time.time() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise RuntimeError(
                    f"server exited unexpectedly with code {process.returncode}\n"
                    f"stdout:\n{stdout}\nstderr:\n{stderr}"
                )
            try:
                response = client.get("/api/subdirectories")
                if response.status_code == 200:
                    break
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(0.1)
        else:
            process.terminate()
            process.wait(timeout=3)
            raise RuntimeError(f"server did not become ready in time: {last_error}")

        clients.append(client)
        processes.append(process)
        return client

    yield _start

    for client in clients:
        client.close()
    for process in processes:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)

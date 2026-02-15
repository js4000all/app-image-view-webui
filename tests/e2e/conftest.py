from __future__ import annotations

import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


@pytest.fixture
def copied_image_root(tmp_path: Path) -> Path:
    source = Path("tests/resources/image_root")
    destination = tmp_path / "image_root"
    shutil.copytree(source, destination)
    return destination


@pytest.fixture
def live_server(free_tcp_port_factory, copied_image_root: Path):
    port = free_tcp_port_factory()
    process = subprocess.Popen(
        [
            "python",
            "app.py",
            str(copied_image_root),
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

    deadline = time.time() + 10
    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise RuntimeError(
                f"server exited unexpectedly with code {process.returncode}\n"
                f"stdout:\n{stdout}\nstderr:\n{stderr}"
            )

        try:
            with urllib.request.urlopen(f"{base_url}/api/subdirectories") as response:
                if response.status == 200:
                    break
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    else:
        process.terminate()
        process.wait(timeout=3)
        raise RuntimeError("server did not become ready in time")

    yield base_url

    if process.poll() is None:
        process.terminate()
        process.wait(timeout=3)


@pytest.fixture(scope="session", autouse=True)
def ensure_playwright_runtime_available() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")

    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as error:  # noqa: BLE001
            message = str(error)
            if "error while loading shared libraries" in message:
                pytest.skip(
                    "Playwright Chromium のシステム依存が不足しています。"
                    " `python -m playwright install --with-deps chromium` を実行してください。"
                )
            raise
        else:
            browser.close()

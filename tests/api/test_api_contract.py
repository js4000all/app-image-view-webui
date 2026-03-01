from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import AppSettings
from app.main import create_app
from app.repositories.filesystem import FileSystemRepository
from app.services.image_service import ResourceRegistry
from app.services.tag_index_service import TagIndexService


def _first_directory_id(client):
    response = client.get("/api/subdirectories")
    assert response.status_code == 200
    subdirectories = response.json()["subdirectories"]
    assert subdirectories
    return subdirectories[0]["directory_id"]


def _first_file_id(client, directory_id: str):
    response = client.get(f"/api/images/{directory_id}")
    assert response.status_code == 200
    images = response.json()["images"]
    assert images
    return images[0]["file_id"]


def test_get_subdirectories_when_non_empty(api_client_factory, copied_image_root):
    client = api_client_factory(copied_image_root)

    response = client.get("/api/subdirectories")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["subdirectories"], list)
    assert len(data["subdirectories"]) == 2
    assert all(isinstance(entry["directory_id"], str) for entry in data["subdirectories"])
    assert all(isinstance(entry["name"], str) for entry in data["subdirectories"])


def test_get_subdirectories_when_empty(api_client_factory, empty_image_root):
    client = api_client_factory(empty_image_root)

    response = client.get("/api/subdirectories")

    assert response.status_code == 200
    assert response.json() == {"subdirectories": []}


def test_get_images_for_existing_and_missing_directory(api_client_factory, copied_image_root):
    client = api_client_factory(copied_image_root)
    directory_id = _first_directory_id(client)

    success = client.get(f"/api/images/{directory_id}")
    missing = client.get("/api/images/not-found-directory-id")

    assert success.status_code == 200
    payload = success.json()
    assert payload["directory_id"] == directory_id
    assert isinstance(payload["subdirectory"], str)
    assert isinstance(payload["images"], list)
    assert payload["images"]
    assert all(isinstance(entry["file_id"], str) for entry in payload["images"])
    assert all(isinstance(entry["name"], str) for entry in payload["images"])
    assert missing.status_code == 404


def test_get_and_head_image_contract(api_client_factory, copied_image_root):
    client = api_client_factory(copied_image_root)
    directory_id = _first_directory_id(client)
    file_id = _first_file_id(client, directory_id)

    get_response = client.get(f"/api/image/{file_id}")
    assert get_response.status_code == 200
    assert get_response.content
    etag = get_response.headers["etag"]

    not_modified = client.get(f"/api/image/{file_id}", headers={"If-None-Match": etag})
    assert not_modified.status_code == 304

    head_response = client.head(f"/api/image/{file_id}")
    assert head_response.status_code == 200
    assert head_response.content == b""

    missing = client.get("/api/image/not-found-file-id")
    assert missing.status_code == 404


def test_get_image_metadata_for_existing_and_missing_file(api_client_factory, copied_image_root):
    client = api_client_factory(copied_image_root)
    directory_id = _first_directory_id(client)
    file_id = _first_file_id(client, directory_id)

    success = client.get(f"/api/image-meta/{file_id}")
    missing = client.get('/api/image-meta/not-found-file-id')

    assert success.status_code == 200
    payload = success.json()
    assert payload["file_id"] == file_id
    assert isinstance(payload["name"], str)
    assert isinstance(payload["directory_id"], str)
    assert isinstance(payload["directory_name"], str)
    assert missing.status_code == 404


def test_delete_image_then_fetch_returns_404(api_client_factory, copied_image_root):
    client = api_client_factory(copied_image_root)
    directory_id = _first_directory_id(client)
    file_id = _first_file_id(client, directory_id)

    delete_response = client.delete(f"/api/image/{file_id}")
    fetch_after_delete = client.get(f"/api/image/{file_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["file_id"] == file_id
    assert fetch_after_delete.status_code == 404


def test_put_subdirectory_rename_success_and_conflict(api_client_factory, copied_image_root):
    client = api_client_factory(copied_image_root)

    list_response = client.get("/api/subdirectories")
    assert list_response.status_code == 200
    subdirs = list_response.json()["subdirectories"]
    assert len(subdirs) >= 2

    rename_target = subdirs[0]
    conflict_name = subdirs[1]["name"]

    rename_response = client.put(
        f"/api/subdirectories/{rename_target['directory_id']}",
        json={"new_name": "renamed-dir"},
    )
    conflict_response = client.put(
        f"/api/subdirectories/{rename_response.json()['directory_id']}",
        json={"new_name": conflict_name},
    )

    assert rename_response.status_code == 200
    renamed_payload = rename_response.json()
    assert renamed_payload["renamed_from"] == rename_target["name"]
    assert renamed_payload["renamed_to"] == "renamed-dir"
    assert conflict_response.status_code == 409

    refreshed = client.get("/api/subdirectories")
    assert refreshed.status_code == 200
    names = [entry["name"] for entry in refreshed.json()["subdirectories"]]
    assert "renamed-dir" in names
    assert rename_target["name"] not in names


def test_tag_index_query_and_refresh(api_client_factory, copied_prompt_image_root):
    client = api_client_factory(copied_prompt_image_root)

    query_response = client.post(
        "/api/tag-index/query",
        json={"tags": ["old male", "best quality"], "mode": "and"},
    )
    assert query_response.status_code == 200
    data = query_response.json()
    assert data["total"] == 2
    assert len(data["file_ids"]) == 2

    refresh_response = client.post("/api/tag-index/refresh")
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["indexed_files"] == 5
    assert refreshed["indexed_tags"] >= 8


def test_tag_index_refresh_job_lifecycle(api_client_factory, copied_prompt_image_root):
    client = api_client_factory(copied_prompt_image_root)

    start_response = client.post("/api/tag-index/refresh-jobs")
    assert start_response.status_code == 200
    job_id = start_response.json()["job_id"]
    assert isinstance(job_id, str)

    terminal = None
    for _ in range(60):
        status_response = client.get(f"/api/tag-index/refresh-jobs/{job_id}")
        assert status_response.status_code == 200
        payload = status_response.json()

        assert payload["job_id"] == job_id
        assert payload["status"] in {"queued", "running", "succeeded", "failed"}
        assert payload["progress_phase"] in {"queued", "listing", "scanning", "applying", "finalizing", "done", "failed"}

        counters = payload["counters"]
        assert {"added", "modified", "deleted", "reindexed"}.issubset(counters.keys())
        assert payload["processed_files"] >= 0
        assert payload["total_files"] >= 0

        if payload["status"] in {"succeeded", "failed"}:
            terminal = payload
            break

        time.sleep(0.05)

    assert terminal is not None
    assert terminal["status"] == "succeeded"
    assert terminal["progress_phase"] == "done"
    assert terminal["indexed_files"] == 5
    assert terminal["indexed_tags"] >= 8
    assert terminal["error"] is None


def test_tag_index_query_works_on_startup_by_loading_db_without_rebuild(tmp_path, monkeypatch):
    static_dir = Path(__file__).resolve().parents[2] / "static"
    source = Path("tests/resources/images_with_prompt/dir1")
    indexed_dir = tmp_path / "indexed"
    indexed_dir.mkdir()
    (indexed_dir / "nested").mkdir()
    (indexed_dir / "00009.png").write_bytes((source / "00009.png").read_bytes())
    (indexed_dir / "nested" / "00010.avif").write_bytes((source / "00010.avif").read_bytes())

    builder = TagIndexService(
        base_dir=indexed_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=tmp_path / "tag_index.sqlite3",
    )
    builder.build_index(indexed_dir)

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    app = create_app(AppSettings.from_paths(base_dir=empty_dir, static_dir=static_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/tag-index/query",
            json={"tags": ["old male", "best quality"], "mode": "and"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["file_ids"]) == 2

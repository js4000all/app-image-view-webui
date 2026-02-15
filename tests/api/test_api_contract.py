from __future__ import annotations


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

    rename_response = client.put(f"/api/subdirectories/{rename_target['directory_id']}", json={"new_name": "renamed-dir"})

    assert rename_response.status_code == 200
    renamed_payload = rename_response.json()
    assert renamed_payload["renamed_from"] == rename_target["name"]
    assert renamed_payload["renamed_to"] == "renamed-dir"

    conflict_response = client.put(
        f"/api/subdirectories/{rename_response.json()['directory_id']}",
        json={"new_name": conflict_name},
    )
    assert conflict_response.status_code == 409

    refreshed = client.get("/api/subdirectories")
    assert refreshed.status_code == 200
    names = [entry["name"] for entry in refreshed.json()["subdirectories"]]
    assert "renamed-dir" in names
    assert rename_target["name"] not in names


def test_put_subdirectory_rename_returns_400_for_invalid_new_name(api_client_factory, copied_image_root):
    client = api_client_factory(copied_image_root)
    directory_id = _first_directory_id(client)

    invalid_names = ["", "   ", ".", "..", "with/slash", "with\\backslash"]
    for invalid_name in invalid_names:
        response = client.put(
            f"/api/subdirectories/{directory_id}",
            json={"new_name": invalid_name},
        )
        assert response.status_code == 400


def test_put_subdirectory_rename_returns_409_for_existing_name(api_client_factory, copied_image_root):
    client = api_client_factory(copied_image_root)

    list_response = client.get("/api/subdirectories")
    assert list_response.status_code == 200
    subdirs = list_response.json()["subdirectories"]
    assert len(subdirs) >= 2

    rename_target = subdirs[0]
    existing_name = subdirs[1]["name"]

    response = client.put(
        f"/api/subdirectories/{rename_target['directory_id']}",
        json={"new_name": existing_name},
    )

    assert response.status_code == 409

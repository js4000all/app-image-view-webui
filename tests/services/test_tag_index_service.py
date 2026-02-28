from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.repositories.filesystem import FileSystemRepository
from app.services.image_service import ResourceRegistry
from app.services.tag_index_service import TagIndexService


def test_build_index_and_query_with_and_or_modes(tmp_path: Path):
    source = Path("tests/resources/images_with_prompt/dir1")
    base_dir = tmp_path / "images"
    nested_dir = base_dir / "nested"
    nested_dir.mkdir(parents=True)
    shutil.copy2(source / "00009.png", nested_dir / "00009.png")
    shutil.copy2(source / "00010.avif", base_dir / "00010.avif")
    shutil.copy2(source / "00025.avif", base_dir / "00025.avif")
    shutil.copy2(source / "00027.avif", nested_dir / "00027.avif")
    shutil.copy2(source / "00029.avif", base_dir / "00029.avif")

    service = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=tmp_path / "tag_index.sqlite3",
    )

    service.build_index(base_dir)

    assert "old male" in service.tag_to_file_ids
    assert "mountain" in service.tag_to_file_ids
    assert "knight" in service.tag_to_file_ids
    assert len(service.file_id_to_tags) == 5
    assert len(service.query(["old male", "best quality"], "and")) == 2
    assert len(service.query(["solo"], "and")) == 2
    assert len(service.query(["knight", "masterpiece"], "and")) == 1
    assert len(service.query(["holding cat", "unknown"], "or")) == 2
    assert service.query(["unknown"], "and") == []

    service.refresh_index()
    assert len(service.file_metadata) == 5



def test_build_index_outputs_progress_bar(tmp_path: Path, capsys):
    source = Path("tests/resources/images_with_prompt/dir1")
    base_dir = tmp_path / "images"
    base_dir.mkdir()
    shutil.copy2(source / "00009.png", base_dir / "00009.png")

    service = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=tmp_path / "tag_index.sqlite3",
    )

    service.build_index(base_dir)
    captured = capsys.readouterr()

    assert "[tag-index] build" in captured.out
    assert "100%" in captured.out


def test_load_index_from_db_restores_in_memory_state(tmp_path: Path):
    source = Path("tests/resources/images_with_prompt/dir1")
    base_dir = tmp_path / "images"
    base_dir.mkdir()
    shutil.copy2(source / "00009.png", base_dir / "00009.png")
    shutil.copy2(source / "00010.avif", base_dir / "00010.avif")
    db_path = tmp_path / "tag_index.sqlite3"

    builder = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=db_path,
    )
    builder.build_index(base_dir)

    loader = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=db_path,
    )
    loaded_count = loader.load_index_from_db()

    assert loaded_count == 2
    assert len(loader.file_id_to_tags) == 2
    assert len(loader.file_metadata) == 2
    assert len(loader.query(["old male", "best quality"], "and")) == 2




def test_refresh_index_outputs_scan_and_apply_progress(tmp_path: Path, capsys, monkeypatch):
    base_dir = tmp_path / "images"
    base_dir.mkdir()
    image_file = base_dir / "001.png"
    image_file.write_bytes(b"v1")

    def fake_extract(_image_path: Path):
        class _Result:
            positive = ["tag-001"]

        return _Result()

    monkeypatch.setattr("app.services.tag_index_service.extract_generation_prompts", fake_extract)

    service = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=tmp_path / "tag_index.sqlite3",
    )
    service.build_index(base_dir)
    capsys.readouterr()

    service.refresh_index()
    captured = capsys.readouterr()

    assert "[tag-index] refresh list" in captured.out
    assert "[tag-index] refresh scan" in captured.out
    assert "[tag-index] refresh apply" in captured.out

def test_refresh_index_only_indexes_added_files(tmp_path: Path, monkeypatch):
    base_dir = tmp_path / "images"
    base_dir.mkdir()
    file1 = base_dir / "001.png"
    file1.write_bytes(b"old")

    extracted: list[str] = []

    def fake_extract(image_path: Path):
        extracted.append(image_path.name)

        class _Result:
            positive = [f"tag-{image_path.stem}"]

        return _Result()

    monkeypatch.setattr("app.services.tag_index_service.extract_generation_prompts", fake_extract)

    service = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=tmp_path / "tag_index.sqlite3",
    )
    service.build_index(base_dir)
    assert extracted == ["001.png"]

    file2 = base_dir / "002.png"
    file2.write_bytes(b"new")
    extracted.clear()

    service.refresh_index()

    assert extracted == ["002.png"]
    assert len(service.file_metadata) == 2
    assert len(service.query(["tag-001"], "and")) == 1
    assert len(service.query(["tag-002"], "and")) == 1


def test_refresh_index_only_reextracts_modified_files(tmp_path: Path, monkeypatch):
    base_dir = tmp_path / "images"
    base_dir.mkdir()
    image_file = base_dir / "001.png"
    image_file.write_bytes(b"v1")

    call_count: dict[str, int] = {}

    def fake_extract(image_path: Path):
        call_count[image_path.name] = call_count.get(image_path.name, 0) + 1

        class _Result:
            positive = ["tag-v1"] if call_count[image_path.name] == 1 else ["tag-v2"]

        return _Result()

    monkeypatch.setattr("app.services.tag_index_service.extract_generation_prompts", fake_extract)

    service = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=tmp_path / "tag_index.sqlite3",
    )
    service.build_index(base_dir)
    assert len(service.query(["tag-v1"], "and")) == 1

    image_file.write_bytes(b"v2")
    extracted_before = dict(call_count)

    service.refresh_index()

    assert call_count["001.png"] == extracted_before["001.png"] + 1
    assert service.query(["tag-v1"], "and") == []
    assert len(service.query(["tag-v2"], "and")) == 1


def test_refresh_index_removes_deleted_files_from_results(tmp_path: Path, monkeypatch):
    base_dir = tmp_path / "images"
    base_dir.mkdir()
    file1 = base_dir / "001.png"
    file2 = base_dir / "002.png"
    file1.write_bytes(b"a")
    file2.write_bytes(b"b")

    def fake_extract(image_path: Path):
        class _Result:
            positive = [f"tag-{image_path.stem}"]

        return _Result()

    monkeypatch.setattr("app.services.tag_index_service.extract_generation_prompts", fake_extract)

    db_path = tmp_path / "tag_index.sqlite3"
    service = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=db_path,
    )
    service.build_index(base_dir)

    file2.unlink()
    service.refresh_index()

    assert len(service.query(["tag-001"], "and")) == 1
    assert service.query(["tag-002"], "and") == []

    with sqlite3.connect(db_path) as conn:
        indexed_count = conn.execute("SELECT COUNT(*) FROM indexed_files").fetchone()[0]
        tag_count = conn.execute("SELECT COUNT(*) FROM file_tags WHERE tag = ?", ("tag-002",)).fetchone()[0]

    assert indexed_count == 1
    assert tag_count == 0

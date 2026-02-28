from __future__ import annotations

import shutil
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

    service = TagIndexService(
        base_dir=base_dir,
        repository=FileSystemRepository(),
        registry=ResourceRegistry(),
        db_path=tmp_path / "tag_index.sqlite3",
    )

    service.build_index(base_dir)

    assert "old male" in service.tag_to_file_ids
    assert len(service.file_id_to_tags) == 2
    assert len(service.query(["old male", "best quality"], "and")) == 2
    assert len(service.query(["holding cat", "unknown"], "or")) == 2
    assert service.query(["unknown"], "and") == []

    service.refresh_index()
    assert len(service.file_metadata) == 2



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

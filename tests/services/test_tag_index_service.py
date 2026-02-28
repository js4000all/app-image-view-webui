from __future__ import annotations

import shutil
from pathlib import Path

from app.repositories.filesystem import FileSystemRepository
from app.services.image_service import ResourceRegistry
from app.services.tag_index_service import TagIndexService


def test_build_index_and_query_with_and_or_modes(tmp_path: Path):
    source = Path("tests/resources/images_with_prompt")
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

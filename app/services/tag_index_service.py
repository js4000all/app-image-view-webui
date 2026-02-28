from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.models.types import FileId
from app.repositories.filesystem import FileSystemRepository
from app.services.image_service import ResourceRegistry
from app.services.prompt_extractor import extract_generation_prompts
from tqdm import tqdm

QueryMode = Literal["and", "or"]


@dataclass(frozen=True)
class FileFingerprint:
    mtime_ns: int
    size: int


@dataclass(frozen=True)
class IndexedFileMeta:
    path: str
    fingerprint: FileFingerprint


@dataclass(frozen=True)
class IndexedRecord:
    file_id: FileId
    fingerprint: FileFingerprint


class TagIndexService:
    def __init__(
        self,
        *,
        base_dir: Path,
        repository: FileSystemRepository,
        registry: ResourceRegistry,
        db_path: Path = Path("tag_index.sqlite3"),
    ) -> None:
        self.base_dir = base_dir
        self.repository = repository
        self.registry = registry
        self.db_path = db_path

        self.tag_to_file_ids: dict[str, set[FileId]] = {}
        self.file_id_to_tags: dict[FileId, list[str]] = {}
        self.file_metadata: dict[FileId, IndexedFileMeta] = {}

        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS indexed_files (
                    file_id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    mtime_ns INTEGER NOT NULL,
                    size INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS file_tags (
                    tag TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    PRIMARY KEY (tag, file_id),
                    FOREIGN KEY (file_id) REFERENCES indexed_files(file_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_file_tags_file_id ON file_tags(file_id);
                """
            )

    def build_index(self, base_dir: Path | None = None) -> None:
        target_base = (base_dir or self.base_dir).resolve()
        image_paths = self.repository.list_images_recursive(target_base)

        tag_to_file_ids: dict[str, set[FileId]] = {}
        file_id_to_tags: dict[FileId, list[str]] = {}
        file_metadata: dict[FileId, IndexedFileMeta] = {}

        with self._connect() as conn:
            conn.execute("DELETE FROM file_tags")
            conn.execute("DELETE FROM indexed_files")

            progress = tqdm(image_paths, desc="[tag-index] build", unit="file", file=sys.stdout)
            for image_path in progress:
                prompt_result = extract_generation_prompts(image_path)
                positive_tags = _normalize_tags(prompt_result.positive if prompt_result else [])
                if positive_tags:
                    file_id = FileId(self.registry.register(image_path))
                    stat_result = image_path.stat()
                    fingerprint = FileFingerprint(mtime_ns=stat_result.st_mtime_ns, size=stat_result.st_size)

                    file_id_to_tags[file_id] = positive_tags
                    file_metadata[file_id] = IndexedFileMeta(path=str(image_path.resolve()), fingerprint=fingerprint)

                    conn.execute(
                        "INSERT INTO indexed_files(file_id, path, mtime_ns, size) VALUES (?, ?, ?, ?)",
                        (file_id, str(image_path.resolve()), fingerprint.mtime_ns, fingerprint.size),
                    )

                    for tag in positive_tags:
                        tag_to_file_ids.setdefault(tag, set()).add(file_id)
                        conn.execute("INSERT INTO file_tags(tag, file_id) VALUES (?, ?)", (tag, file_id))
            progress.close()

        self.tag_to_file_ids = tag_to_file_ids
        self.file_id_to_tags = file_id_to_tags
        self.file_metadata = file_metadata

    def load_index_from_db(self) -> int:
        tag_to_file_ids: dict[str, set[FileId]] = {}
        file_id_to_tags: dict[FileId, list[str]] = {}
        file_metadata: dict[FileId, IndexedFileMeta] = {}

        with self._connect() as conn:
            indexed_files = conn.execute("SELECT file_id, path, mtime_ns, size FROM indexed_files")
            for file_id_raw, path, mtime_ns, size in indexed_files:
                file_id = FileId(file_id_raw)
                fingerprint = FileFingerprint(mtime_ns=mtime_ns, size=size)
                file_metadata[file_id] = IndexedFileMeta(path=path, fingerprint=fingerprint)
                file_id_to_tags[file_id] = []

            file_tags = conn.execute("SELECT tag, file_id FROM file_tags")
            for tag, file_id_raw in file_tags:
                file_id = FileId(file_id_raw)
                if file_id not in file_metadata:
                    continue
                file_id_to_tags[file_id].append(tag)
                tag_to_file_ids.setdefault(tag, set()).add(file_id)

        self.tag_to_file_ids = tag_to_file_ids
        self.file_id_to_tags = file_id_to_tags
        self.file_metadata = file_metadata
        return len(file_metadata)

    def refresh_index(self) -> None:
        target_base = self.base_dir.resolve()
        image_paths = self.repository.list_images_recursive(target_base)

        current_files: dict[str, tuple[Path, FileFingerprint]] = {}
        for image_path in image_paths:
            resolved_path = image_path.resolve()
            stat_result = resolved_path.stat()
            current_files[str(resolved_path)] = (
                resolved_path,
                FileFingerprint(mtime_ns=stat_result.st_mtime_ns, size=stat_result.st_size),
            )

        with self._connect() as conn:
            db_files: dict[str, IndexedRecord] = {}
            rows = conn.execute("SELECT file_id, path, mtime_ns, size FROM indexed_files")
            for file_id_raw, path, mtime_ns, size in rows:
                db_files[path] = IndexedRecord(
                    file_id=FileId(file_id_raw),
                    fingerprint=FileFingerprint(mtime_ns=mtime_ns, size=size),
                )

            added_paths = sorted(path for path in current_files if path not in db_files)
            deleted_paths = sorted(path for path in db_files if path not in current_files)
            modified_paths = sorted(
                path
                for path in current_files
                if path in db_files and current_files[path][1] != db_files[path].fingerprint
            )

            for path in deleted_paths:
                file_id = db_files[path].file_id
                conn.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id,))
                conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (file_id,))

            reindex_paths = added_paths + modified_paths
            progress = tqdm(reindex_paths, desc="[tag-index] refresh", unit="file", file=sys.stdout)
            for path in progress:
                image_path, fingerprint = current_files[path]

                if path in db_files:
                    old_file_id = db_files[path].file_id
                    conn.execute("DELETE FROM file_tags WHERE file_id = ?", (old_file_id,))
                    conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (old_file_id,))

                prompt_result = extract_generation_prompts(image_path)
                positive_tags = _normalize_tags(prompt_result.positive if prompt_result else [])
                if not positive_tags:
                    continue

                file_id = FileId(self.registry.register(image_path))
                conn.execute(
                    "INSERT INTO indexed_files(file_id, path, mtime_ns, size) VALUES (?, ?, ?, ?)",
                    (file_id, path, fingerprint.mtime_ns, fingerprint.size),
                )
                for tag in positive_tags:
                    conn.execute("INSERT INTO file_tags(tag, file_id) VALUES (?, ?)", (tag, file_id))
            progress.close()

        self.load_index_from_db()

    def query(self, tags: list[str], mode: QueryMode) -> list[FileId]:
        normalized_tags = _normalize_tags(tags)
        if not normalized_tags:
            return []

        matched_sets = [self.tag_to_file_ids.get(tag, set()) for tag in normalized_tags]
        if not matched_sets:
            return []

        if mode == "and":
            matched = set.intersection(*matched_sets) if matched_sets else set()
        else:
            matched = set.union(*matched_sets)

        return sorted(matched)


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_tag in tags:
        tag = raw_tag.strip().casefold()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized

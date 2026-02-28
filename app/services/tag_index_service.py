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

QueryMode = Literal["and", "or"]


@dataclass(frozen=True)
class FileFingerprint:
    mtime_ns: int
    size: int


@dataclass(frozen=True)
class IndexedFileMeta:
    path: str
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
        total = len(image_paths)

        self._print_progress(current=0, total=total)

        with self._connect() as conn:
            conn.execute("DELETE FROM file_tags")
            conn.execute("DELETE FROM indexed_files")

            for index, image_path in enumerate(image_paths, start=1):
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

                self._print_progress(current=index, total=total)

        self.tag_to_file_ids = tag_to_file_ids
        self.file_id_to_tags = file_id_to_tags
        self.file_metadata = file_metadata

    def _print_progress(self, *, current: int, total: int) -> None:
        if total == 0:
            message = "[tag-index] build progress: 0/0 (100%)"
        else:
            percent = int((current / total) * 100)
            bar_width = 20
            filled = int(bar_width * current / total)
            bar = "#" * filled + "-" * (bar_width - filled)
            message = f"[tag-index] build progress: [{bar}] {current}/{total} ({percent}%)"

        end = "\n" if current >= total else "\r"
        print(message, file=sys.stdout, end=end, flush=True)

    def refresh_index(self) -> None:
        # NOTE: Full rebuild for now. `file_metadata` stores mtime/size fingerprints
        # that enable future diff-based refreshes.
        self.build_index(self.base_dir)

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

from __future__ import annotations

import os
import sqlite3
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Literal

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
    directory_id: str


@dataclass(frozen=True)
class IndexedRecord:
    file_id: FileId
    directory_id: str
    fingerprint: FileFingerprint


@dataclass
class RefreshJobCounters:
    added: int = 0
    modified: int = 0
    deleted: int = 0
    reindexed: int = 0


@dataclass
class RefreshJobState:
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    progress_phase: Literal["queued", "listing", "scanning", "applying", "finalizing", "done", "failed"] = "queued"
    processed_files: int = 0
    total_files: int = 0
    indexed_files: int = 0
    indexed_tags: int = 0
    counters: RefreshJobCounters = field(default_factory=RefreshJobCounters)
    error: str | None = None


class TagIndexService:
    def __init__(
        self,
        *,
        roots: dict[str, Path] | None = None,
        base_dir: Path | None = None,
        repository: FileSystemRepository,
        registry: ResourceRegistry,
        db_path: Path = Path("tag_index.sqlite3"),
        max_workers: int | None = None,
    ) -> None:
        if roots is None:
            if base_dir is None:
                raise ValueError("Either roots or base_dir is required")
            roots = {"d1": base_dir}
        self.roots = {k: p.resolve() for k, p in roots.items()}
        self.repository = repository
        self.registry = registry
        self.db_path = db_path
        self.max_workers = max_workers if max_workers is not None else min(os.cpu_count() or 1, 8)
        if self.max_workers < 1:
            raise ValueError("max_workers must be greater than 0")

        self.tag_to_file_ids: dict[str, set[FileId]] = {}
        self.file_id_to_tags: dict[FileId, list[str]] = {}
        self.file_metadata: dict[FileId, IndexedFileMeta] = {}

        self._jobs: dict[str, RefreshJobState] = {}
        self._job_events: dict[str, threading.Event] = {}
        self._jobs_lock = threading.Lock()

        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS indexed_directories (
                    directory_id TEXT PRIMARY KEY,
                    root_key TEXT NOT NULL,
                    directory_name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    UNIQUE(root_key, directory_name)
                );

                CREATE TABLE IF NOT EXISTS indexed_files (
                    file_id TEXT PRIMARY KEY,
                    directory_id TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    FOREIGN KEY (directory_id) REFERENCES indexed_directories(directory_id) ON DELETE CASCADE
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

    def _list_index_directories(self) -> list[Path]:
        directories: list[Path] = []
        for root_path in self.roots.values():
            directories.append(root_path)
            directories.extend(self.repository.list_subdirectories(root_path))
        return sorted(set(directories))

    def _collect_directory_rows(self) -> list[tuple[str, str, str, str, int]]:
        rows: list[tuple[str, str, str, str, int]] = []
        for directory in self._list_index_directories():
            directory_id, root_key, directory_name = self.registry.get_directory_identity(directory)
            stat_result = directory.stat()
            rows.append((directory_id, root_key, directory_name, str(directory.resolve()), stat_result.st_mtime_ns))
        return rows

    def _list_images_for_roots(self) -> list[Path]:
        images: list[Path] = []
        for root_path in self.roots.values():
            images.extend(self.repository.list_images_recursive(root_path))
        return sorted(images)

    def _snapshot_job(self, job_id: str) -> RefreshJobState | None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return RefreshJobState(
                job_id=job.job_id,
                status=job.status,
                progress_phase=job.progress_phase,
                processed_files=job.processed_files,
                total_files=job.total_files,
                indexed_files=job.indexed_files,
                indexed_tags=job.indexed_tags,
                counters=RefreshJobCounters(**asdict(job.counters)),
                error=job.error,
            )

    def start_refresh_job(self) -> str:
        job_id = uuid.uuid4().hex
        with self._jobs_lock:
            self._jobs[job_id] = RefreshJobState(job_id=job_id)
            self._job_events[job_id] = threading.Event()

        thread = threading.Thread(target=self._run_refresh_job, args=(job_id,), daemon=True)
        thread.start()
        return job_id

    def _run_refresh_job(self, job_id: str) -> None:
        try:
            self.refresh_index(progress_callback=lambda **payload: self._update_job(job_id, **payload))
            self._update_job(
                job_id,
                status="succeeded",
                progress_phase="done",
                processed_files=0,
                total_files=0,
                indexed_files=len(self.file_id_to_tags),
                indexed_tags=len(self.tag_to_file_ids),
            )
        except Exception as exc:
            self._update_job(job_id, status="failed", progress_phase="failed", error=str(exc))
        finally:
            event = self._job_events.get(job_id)
            if event is not None:
                event.set()

    def _update_job(self, job_id: str, **fields: object) -> None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                if value is None:
                    continue
                if key == "counters" and isinstance(value, dict):
                    job.counters = RefreshJobCounters(**value)
                    continue
                setattr(job, key, value)

    def get_refresh_job_status(self, job_id: str) -> RefreshJobState | None:
        return self._snapshot_job(job_id)

    def wait_for_job(self, job_id: str) -> RefreshJobState:
        event = self._job_events.get(job_id)
        if event is None:
            raise KeyError(job_id)
        event.wait()
        status = self._snapshot_job(job_id)
        if status is None:
            raise KeyError(job_id)
        return status

    def build_index(self, base_dir: Path | None = None) -> None:
        image_paths = self._list_images_for_roots()

        failed_paths: list[str] = []
        file_rows: list[tuple[str, str, str, str, int, int]] = []
        tag_rows: list[tuple[str, str]] = []

        progress = tqdm(total=len(image_paths), desc="[tag-index] build", unit="file", file=sys.stdout)
        for image_path in image_paths:
            progress.update(1)
            try:
                prompt_result = extract_generation_prompts(image_path)
            except Exception:
                failed_paths.append(str(image_path.resolve()))
                continue

            positive_tags = _normalize_tags(prompt_result.positive if prompt_result else [])
            if not positive_tags:
                continue

            directory_path = image_path.parent
            directory_id = self.registry.register_directory(directory_path)
            file_id = FileId(self.registry.register_file(image_path))
            stat_result = image_path.stat()
            file_rows.append((file_id, directory_id, str(image_path.resolve()), image_path.name, stat_result.st_mtime_ns, stat_result.st_size))
            for tag in positive_tags:
                tag_rows.append((tag, file_id))
        progress.close()

        with self._connect() as conn:
            conn.execute("DELETE FROM file_tags")
            conn.execute("DELETE FROM indexed_files")
            conn.execute("DELETE FROM indexed_directories")
            conn.executemany(
                "INSERT INTO indexed_directories(directory_id, root_key, directory_name, path, mtime_ns) VALUES (?, ?, ?, ?, ?)",
                self._collect_directory_rows(),
            )
            if file_rows:
                conn.executemany(
                    "INSERT INTO indexed_files(file_id, directory_id, path, name, mtime_ns, size) VALUES (?, ?, ?, ?, ?, ?)",
                    file_rows,
                )
            if tag_rows:
                conn.executemany("INSERT INTO file_tags(tag, file_id) VALUES (?, ?)", tag_rows)

        if failed_paths:
            tqdm.write(
                "[tag-index] build skipped files due to extraction errors "
                f"(count={len(failed_paths)}):\n" + "\n".join(failed_paths),
                file=sys.stdout,
            )

        self.load_index_from_db(reconcile_directories=False)

    def _reconcile_directory_index(self, conn: sqlite3.Connection) -> None:
        current_rows = self._collect_directory_rows()
        current_by_path = {path: (directory_id, root_key, directory_name, mtime_ns) for directory_id, root_key, directory_name, path, mtime_ns in current_rows}

        db_dirs = {
            path: (directory_id, mtime_ns)
            for directory_id, path, mtime_ns in conn.execute("SELECT directory_id, path, mtime_ns FROM indexed_directories")
        }

        changed_dirs = sorted(
            path
            for path, (_d_id, _rk, _dn, mtime_ns) in current_by_path.items()
            if path not in db_dirs or db_dirs[path][1] != mtime_ns
        )
        deleted_dirs = sorted(path for path in db_dirs if path not in current_by_path)

        if changed_dirs or deleted_dirs:
            self._reconcile_files_for_directories(conn, changed_dirs, deleted_dirs)

        conn.execute("DELETE FROM indexed_directories")
        conn.executemany(
            "INSERT INTO indexed_directories(directory_id, root_key, directory_name, path, mtime_ns) VALUES (?, ?, ?, ?, ?)",
            current_rows,
        )

    def _reconcile_files_for_directories(self, conn: sqlite3.Connection, changed_dirs: list[str], deleted_dirs: list[str]) -> None:
        db_files_by_path: dict[str, IndexedRecord] = {}
        for file_id, directory_id, path, mtime_ns, size in conn.execute(
            "SELECT file_id, directory_id, path, mtime_ns, size FROM indexed_files"
        ):
            db_files_by_path[path] = IndexedRecord(file_id=FileId(file_id), directory_id=directory_id, fingerprint=FileFingerprint(mtime_ns=mtime_ns, size=size))

        current_files: dict[str, tuple[Path, FileFingerprint]] = {}
        changed_paths: list[str] = []
        for directory_path in changed_dirs:
            directory = Path(directory_path)
            if not directory.exists() or not directory.is_dir():
                continue
            for image_path in self.repository.list_images_recursive(directory):
                stat_result = image_path.stat()
                resolved = str(image_path.resolve())
                current_files[resolved] = (image_path, FileFingerprint(mtime_ns=stat_result.st_mtime_ns, size=stat_result.st_size))
                changed_paths.append(resolved)

        db_changed = {p: rec for p, rec in db_files_by_path.items() if str(Path(p).parent).startswith(tuple(changed_dirs))}
        added_paths = sorted(path for path in current_files if path not in db_changed)
        modified_paths = sorted(
            path for path in current_files if path in db_changed and current_files[path][1] != db_changed[path].fingerprint
        )

        deleted_paths = sorted(path for path in db_changed if path not in current_files)
        for deleted_dir in deleted_dirs:
            for path in db_files_by_path:
                if path.startswith(f"{deleted_dir}{os.sep}"):
                    deleted_paths.append(path)
        deleted_paths = sorted(set(deleted_paths))

        for path in deleted_paths:
            file_id = db_files_by_path[path].file_id
            conn.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (file_id,))

        for path in added_paths + modified_paths:
            image_path, fingerprint = current_files[path]
            if path in db_files_by_path:
                old_file_id = db_files_by_path[path].file_id
                conn.execute("DELETE FROM file_tags WHERE file_id = ?", (old_file_id,))
                conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (old_file_id,))

            prompt_result = extract_generation_prompts(image_path)
            positive_tags = _normalize_tags(prompt_result.positive if prompt_result else [])
            if not positive_tags:
                continue

            directory_id = self.registry.register_directory(image_path.parent)
            file_id = FileId(self.registry.register_file(image_path))
            conn.execute(
                "INSERT INTO indexed_files(file_id, directory_id, path, name, mtime_ns, size) VALUES (?, ?, ?, ?, ?, ?)",
                (file_id, directory_id, path, image_path.name, fingerprint.mtime_ns, fingerprint.size),
            )
            for tag in positive_tags:
                conn.execute("INSERT INTO file_tags(tag, file_id) VALUES (?, ?)", (tag, file_id))

    def load_index_from_db(self, *, reconcile_directories: bool = True) -> int:
        with self._connect() as conn:
            if reconcile_directories:
                self._reconcile_directory_index(conn)

            tag_to_file_ids: dict[str, set[FileId]] = {}
            file_id_to_tags: dict[FileId, list[str]] = {}
            file_metadata: dict[FileId, IndexedFileMeta] = {}

            for file_id_raw, directory_id, path, mtime_ns, size in conn.execute(
                "SELECT file_id, directory_id, path, mtime_ns, size FROM indexed_files"
            ):
                file_id = FileId(file_id_raw)
                resolved_path = Path(path).resolve()
                if not resolved_path.exists():
                    continue
                in_roots = any(resolved_path == root or resolved_path.is_relative_to(root) for root in self.roots.values())
                if in_roots:
                    if FileId(self.registry.register_file(resolved_path)) != file_id:
                        continue
                file_metadata[file_id] = IndexedFileMeta(
                    path=str(resolved_path),
                    directory_id=directory_id,
                    fingerprint=FileFingerprint(mtime_ns=mtime_ns, size=size),
                )
                file_id_to_tags[file_id] = []

            for tag, file_id_raw in conn.execute("SELECT tag, file_id FROM file_tags"):
                file_id = FileId(file_id_raw)
                if file_id not in file_metadata:
                    continue
                file_id_to_tags[file_id].append(tag)
                tag_to_file_ids.setdefault(tag, set()).add(file_id)

        self.tag_to_file_ids = tag_to_file_ids
        self.file_id_to_tags = file_id_to_tags
        self.file_metadata = file_metadata
        return len(file_metadata)

    def refresh_index(self, progress_callback: Callable[..., None] | None = None) -> None:
        if progress_callback is not None:
            progress_callback(status="running", progress_phase="listing", processed_files=0, total_files=0)
        tqdm.write("[tag-index] refresh list", file=sys.stdout)

        images = self._list_images_for_roots()

        if progress_callback is not None:
            progress_callback(status="running", progress_phase="scanning", processed_files=0, total_files=len(images))
        scan_progress = tqdm(total=len(images), desc="[tag-index] refresh scan", unit="file", file=sys.stdout)
        for index, _ in enumerate(images, start=1):
            scan_progress.update(1)
            if progress_callback is not None:
                progress_callback(status="running", progress_phase="scanning", processed_files=index, total_files=len(images))
        scan_progress.close()

        if progress_callback is not None:
            progress_callback(status="running", progress_phase="applying", processed_files=0, total_files=0)
        tqdm.write("[tag-index] refresh apply", file=sys.stdout)

        with self._connect() as conn:
            self._reconcile_directory_index(conn)

        self.load_index_from_db(reconcile_directories=False)

        if progress_callback is not None:
            progress_callback(
                status="running",
                progress_phase="finalizing",
                indexed_files=len(self.file_id_to_tags),
                indexed_tags=len(self.tag_to_file_ids),
            )

    def query(self, tags: list[str], mode: QueryMode) -> list[FileId]:
        normalized_tags = _normalize_tags(tags)
        if not normalized_tags:
            return []

        matched_sets = [self.tag_to_file_ids.get(tag, set()) for tag in normalized_tags]
        if mode == "and":
            matched = set.intersection(*matched_sets) if matched_sets else set()
        else:
            matched = set.union(*matched_sets)

        return sorted(matched)

    def list_tags(self) -> list[tuple[str, int]]:
        return sorted(((tag, len(ids)) for tag, ids in self.tag_to_file_ids.items()), key=lambda item: (-item[1], item[0]))

    def list_tag_registry(self) -> list[tuple[str, list[FileId]]]:
        return sorted(((tag, sorted(file_ids)) for tag, file_ids in self.tag_to_file_ids.items()), key=lambda item: item[0])


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

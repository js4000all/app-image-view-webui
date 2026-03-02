from __future__ import annotations

import os
import sqlite3
import sys
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
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


@dataclass(frozen=True)
class IndexedRecord:
    file_id: FileId
    fingerprint: FileFingerprint


@dataclass(frozen=True)
class IndexedDirectory:
    path: str
    mtime_ns: int


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
        base_dir: Path,
        repository: FileSystemRepository,
        registry: ResourceRegistry,
        db_path: Path = Path("tag_index.sqlite3"),
        max_workers: int | None = None,
    ) -> None:
        self.base_dir = base_dir
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

                CREATE TABLE IF NOT EXISTS indexed_directories (
                    path TEXT PRIMARY KEY,
                    mtime_ns INTEGER NOT NULL
                );
                """
            )

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
            self._update_job(
                job_id,
                status="failed",
                progress_phase="failed",
                error=str(exc),
            )
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
        target_base = (base_dir or self.base_dir).resolve()
        image_paths = self.repository.list_images_recursive(target_base)
        directory_rows = self._collect_directory_rows(target_base)

        tag_to_file_ids: dict[str, set[FileId]] = {}
        file_id_to_tags: dict[FileId, list[str]] = {}
        file_metadata: dict[FileId, IndexedFileMeta] = {}

        failed_paths: list[str] = []
        index_rows: list[tuple[str, str, int, int]] = []
        tag_rows: list[tuple[str, str]] = []
        batch_size = 200

        with self._connect() as conn:
            conn.execute("DELETE FROM file_tags")
            conn.execute("DELETE FROM indexed_files")
            conn.execute("DELETE FROM indexed_directories")

            progress = tqdm(total=len(image_paths), desc="[tag-index] build", unit="file", file=sys.stdout)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures: dict[Future, Path] = {
                    executor.submit(extract_generation_prompts, image_path): image_path for image_path in image_paths
                }
                for future in as_completed(futures):
                    image_path = futures[future]
                    progress.update(1)
                    try:
                        prompt_result = future.result()
                    except Exception:
                        failed_paths.append(str(image_path.resolve()))
                        continue

                    positive_tags = _normalize_tags(prompt_result.positive if prompt_result else [])
                    if not positive_tags:
                        continue

                    file_id = FileId(self.registry.register_file(image_path))
                    stat_result = image_path.stat()
                    fingerprint = FileFingerprint(mtime_ns=stat_result.st_mtime_ns, size=stat_result.st_size)

                    file_id_to_tags[file_id] = positive_tags
                    file_metadata[file_id] = IndexedFileMeta(path=str(image_path.resolve()), fingerprint=fingerprint)
                    index_rows.append((file_id, str(image_path.resolve()), fingerprint.mtime_ns, fingerprint.size))

                    for tag in positive_tags:
                        tag_to_file_ids.setdefault(tag, set()).add(file_id)
                        tag_rows.append((tag, file_id))

                    if len(index_rows) >= batch_size:
                        conn.executemany(
                            "INSERT INTO indexed_files(file_id, path, mtime_ns, size) VALUES (?, ?, ?, ?)",
                            index_rows,
                        )
                        index_rows.clear()

                    if len(tag_rows) >= batch_size:
                        conn.executemany("INSERT INTO file_tags(tag, file_id) VALUES (?, ?)", tag_rows)
                        tag_rows.clear()

            if index_rows:
                conn.executemany(
                    "INSERT INTO indexed_files(file_id, path, mtime_ns, size) VALUES (?, ?, ?, ?)",
                    index_rows,
                )
            if tag_rows:
                conn.executemany("INSERT INTO file_tags(tag, file_id) VALUES (?, ?)", tag_rows)
            conn.executemany(
                "INSERT INTO indexed_directories(path, mtime_ns) VALUES (?, ?)",
                directory_rows,
            )
            progress.close()

            if failed_paths:
                tqdm.write(
                    "[tag-index] build skipped files due to extraction errors "
                    f"(count={len(failed_paths)}):\n" + "\n".join(failed_paths),
                    file=sys.stdout,
                )

        self.tag_to_file_ids = tag_to_file_ids
        self.file_id_to_tags = file_id_to_tags
        self.file_metadata = file_metadata

    def load_index_from_db(self, *, reconcile_directories: bool = True) -> int:
        tag_to_file_ids: dict[str, set[FileId]] = {}
        file_id_to_tags: dict[FileId, list[str]] = {}
        file_metadata: dict[FileId, IndexedFileMeta] = {}

        with self._connect() as conn:
            if reconcile_directories:
                self._reconcile_directory_index(conn)

            indexed_files = conn.execute("SELECT file_id, path, mtime_ns, size FROM indexed_files")
            for file_id_raw, path, mtime_ns, size in indexed_files:
                file_id = FileId(file_id_raw)
                resolved_path = Path(path).resolve()
                if resolved_path.is_relative_to(self.base_dir):
                    registered_file_id = FileId(self.registry.register_file(resolved_path))
                    if registered_file_id != file_id:
                        continue

                fingerprint = FileFingerprint(mtime_ns=mtime_ns, size=size)
                file_metadata[file_id] = IndexedFileMeta(path=str(resolved_path), fingerprint=fingerprint)
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

    def _reconcile_directory_index(self, conn: sqlite3.Connection) -> None:
        target_base = self.base_dir.resolve()
        directory_rows = self._collect_directory_rows_with_progress(target_base)
        current_directories = {path: mtime_ns for path, mtime_ns in directory_rows}

        db_directories: dict[str, IndexedDirectory] = {}
        rows = conn.execute("SELECT path, mtime_ns FROM indexed_directories")
        for path, mtime_ns in rows:
            db_directories[path] = IndexedDirectory(path=path, mtime_ns=mtime_ns)

        changed_directories = sorted(
            path
            for path, mtime_ns in current_directories.items()
            if path not in db_directories or db_directories[path].mtime_ns != mtime_ns
        )
        deleted_directories = sorted(path for path in db_directories if path not in current_directories)

        if not changed_directories and not deleted_directories:
            return

        self._reconcile_files_for_directories(conn, changed_directories, deleted_directories)

        conn.execute("DELETE FROM indexed_directories")
        conn.executemany(
            "INSERT INTO indexed_directories(path, mtime_ns) VALUES (?, ?)",
            directory_rows,
        )

    def _reconcile_files_for_directories(
        self,
        conn: sqlite3.Connection,
        changed_directories: list[str],
        deleted_directories: list[str],
    ) -> None:
        db_files_in_changed_dirs: dict[str, IndexedRecord] = {}

        for directory_path in changed_directories:
            for file_id_raw, path, mtime_ns, size in conn.execute(
                "SELECT file_id, path, mtime_ns, size FROM indexed_files WHERE path LIKE ?",
                (f"{directory_path}{os.sep}%",),
            ):
                db_files_in_changed_dirs[path] = IndexedRecord(
                    file_id=FileId(file_id_raw),
                    fingerprint=FileFingerprint(mtime_ns=mtime_ns, size=size),
                )

        current_files: dict[str, tuple[Path, FileFingerprint]] = {}
        for directory_path in changed_directories:
            directory = Path(directory_path)
            if not directory.exists() or not directory.is_dir():
                continue
            for image_path in self.repository.list_images(directory):
                stat_result = image_path.stat()
                current_files[str(image_path.resolve())] = (
                    image_path,
                    FileFingerprint(mtime_ns=stat_result.st_mtime_ns, size=stat_result.st_size),
                )

        added_paths = sorted(path for path in current_files if path not in db_files_in_changed_dirs)
        modified_paths = sorted(
            path
            for path in current_files
            if path in db_files_in_changed_dirs and current_files[path][1] != db_files_in_changed_dirs[path].fingerprint
        )
        deleted_paths = sorted(path for path in db_files_in_changed_dirs if path not in current_files)

        for directory_path in deleted_directories:
            for file_id_raw, path in conn.execute(
                "SELECT file_id, path FROM indexed_files WHERE path LIKE ?",
                (f"{directory_path}{os.sep}%",),
            ):
                conn.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id_raw,))
                conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (file_id_raw,))

        for path in deleted_paths:
            file_id = db_files_in_changed_dirs[path].file_id
            conn.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (file_id,))

        for path in added_paths + modified_paths:
            image_path, fingerprint = current_files[path]

            if path in db_files_in_changed_dirs:
                old_file_id = db_files_in_changed_dirs[path].file_id
                conn.execute("DELETE FROM file_tags WHERE file_id = ?", (old_file_id,))
                conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (old_file_id,))

            prompt_result = extract_generation_prompts(image_path)
            positive_tags = _normalize_tags(prompt_result.positive if prompt_result else [])
            if not positive_tags:
                continue

            file_id = FileId(self.registry.register_file(image_path))
            conn.execute(
                "INSERT INTO indexed_files(file_id, path, mtime_ns, size) VALUES (?, ?, ?, ?)",
                (file_id, path, fingerprint.mtime_ns, fingerprint.size),
            )
            for tag in positive_tags:
                conn.execute("INSERT INTO file_tags(tag, file_id) VALUES (?, ?)", (tag, file_id))


    def _collect_directory_rows_with_progress(self, target_base: Path) -> list[tuple[str, int]]:
        done = threading.Event()

        def _tick_listing_progress() -> None:
            progress = tqdm(desc="[tag-index] refresh list", unit="dir", file=sys.stdout)
            while not done.wait(0.1):
                progress.update(1)
            progress.close()

        ticker = threading.Thread(target=_tick_listing_progress, daemon=True)
        ticker.start()
        try:
            return self._collect_directory_rows(target_base)
        finally:
            done.set()
            ticker.join()

    def _collect_directory_rows(self, target_base: Path) -> list[tuple[str, int]]:
        directories = [target_base, *(entry for entry in target_base.rglob("*") if entry.is_dir())]
        rows: list[tuple[str, int]] = []
        for directory in sorted(directories):
            stat_result = directory.stat()
            rows.append((str(directory.resolve()), stat_result.st_mtime_ns))
        return rows

    def refresh_index(self, progress_callback: Callable[..., None] | None = None) -> None:
        target_base = self.base_dir.resolve()
        directory_rows = self._collect_directory_rows_with_progress(target_base)
        if progress_callback is not None:
            progress_callback(status="running", progress_phase="listing")
        current_directories = {path: mtime_ns for path, mtime_ns in directory_rows}

        with self._connect() as conn:
            db_files: dict[str, IndexedRecord] = {}
            rows = conn.execute("SELECT file_id, path, mtime_ns, size FROM indexed_files")
            for file_id_raw, path, mtime_ns, size in rows:
                db_files[path] = IndexedRecord(
                    file_id=FileId(file_id_raw),
                    fingerprint=FileFingerprint(mtime_ns=mtime_ns, size=size),
                )

            db_directories: dict[str, IndexedDirectory] = {}
            rows = conn.execute("SELECT path, mtime_ns FROM indexed_directories")
            for path, mtime_ns in rows:
                db_directories[path] = IndexedDirectory(path=path, mtime_ns=mtime_ns)

            changed_directories = sorted(
                path
                for path, mtime_ns in current_directories.items()
                if path not in db_directories or db_directories[path].mtime_ns != mtime_ns
            )
            deleted_directories = sorted(path for path in db_directories if path not in current_directories)

            changed_directory_files: list[Path] = []
            for directory_path in changed_directories:
                directory = Path(directory_path)
                changed_directory_files.extend(self.repository.list_images(directory))

            current_files: dict[str, tuple[Path, FileFingerprint]] = {}
            scan_progress = tqdm(
                changed_directory_files,
                desc="[tag-index] refresh scan",
                unit="file",
                file=sys.stdout,
            )
            for index, image_path in enumerate(scan_progress, start=1):
                resolved_path = image_path.resolve()
                stat_result = resolved_path.stat()
                current_files[str(resolved_path)] = (
                    resolved_path,
                    FileFingerprint(mtime_ns=stat_result.st_mtime_ns, size=stat_result.st_size),
                )
                if progress_callback is not None:
                    progress_callback(
                        status="running",
                        progress_phase="scanning",
                        processed_files=index,
                        total_files=len(changed_directory_files),
                    )
            scan_progress.close()

            db_files_in_changed_dirs = {
                path: record
                for path, record in db_files.items()
                if str(Path(path).parent) in changed_directories
            }

            added_paths = sorted(path for path in current_files if path not in db_files_in_changed_dirs)
            modified_paths = sorted(
                path
                for path in current_files
                if path in db_files_in_changed_dirs and current_files[path][1] != db_files_in_changed_dirs[path].fingerprint
            )
            deleted_paths = sorted(path for path in db_files_in_changed_dirs if path not in current_files)

            for directory_path in deleted_directories:
                deleted_paths.extend(
                    path for path in db_files if path == directory_path or path.startswith(f"{directory_path}{os.sep}")
                )
            deleted_paths = sorted(set(deleted_paths))

            reindex_paths = added_paths + modified_paths
            apply_total = len(deleted_paths) + len(reindex_paths)
            if progress_callback is not None:
                progress_callback(
                    status="running",
                    progress_phase="applying",
                    processed_files=0,
                    total_files=apply_total,
                    counters={
                        "added": len(added_paths),
                        "modified": len(modified_paths),
                        "deleted": len(deleted_paths),
                        "reindexed": len(reindex_paths),
                    },
                )
            apply_progress = tqdm(total=apply_total, desc="[tag-index] refresh apply", unit="file", file=sys.stdout)

            applied_count = 0
            for path in deleted_paths:
                file_id = db_files[path].file_id
                conn.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id,))
                conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (file_id,))
                apply_progress.update(1)
                applied_count += 1
                if progress_callback is not None:
                    progress_callback(
                        status="running",
                        progress_phase="applying",
                        processed_files=applied_count,
                        total_files=apply_total,
                    )

            for path in reindex_paths:
                image_path, fingerprint = current_files[path]

                if path in db_files:
                    old_file_id = db_files[path].file_id
                    conn.execute("DELETE FROM file_tags WHERE file_id = ?", (old_file_id,))
                    conn.execute("DELETE FROM indexed_files WHERE file_id = ?", (old_file_id,))

                prompt_result = extract_generation_prompts(image_path)
                positive_tags = _normalize_tags(prompt_result.positive if prompt_result else [])
                apply_progress.update(1)
                applied_count += 1
                if progress_callback is not None:
                    progress_callback(
                        status="running",
                        progress_phase="applying",
                        processed_files=applied_count,
                        total_files=apply_total,
                    )
                if not positive_tags:
                    continue

                file_id = FileId(self.registry.register_file(image_path))
                conn.execute(
                    "INSERT INTO indexed_files(file_id, path, mtime_ns, size) VALUES (?, ?, ?, ?)",
                    (file_id, path, fingerprint.mtime_ns, fingerprint.size),
                )
                for tag in positive_tags:
                    conn.execute("INSERT INTO file_tags(tag, file_id) VALUES (?, ?)", (tag, file_id))

            conn.execute("DELETE FROM indexed_directories")
            conn.executemany(
                "INSERT INTO indexed_directories(path, mtime_ns) VALUES (?, ?)",
                directory_rows,
            )
            apply_progress.close()

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
        if not matched_sets:
            return []

        if mode == "and":
            matched = set.intersection(*matched_sets) if matched_sets else set()
        else:
            matched = set.union(*matched_sets)

        return sorted(matched)

    def list_tags(self) -> list[tuple[str, int]]:
        return sorted(
            ((tag, len(file_ids)) for tag, file_ids in self.tag_to_file_ids.items()),
            key=lambda item: (-item[1], item[0]),
        )

    def list_tag_registry(self) -> list[tuple[str, list[FileId]]]:
        return sorted(
            ((tag, sorted(file_ids)) for tag, file_ids in self.tag_to_file_ids.items()),
            key=lambda item: item[0],
        )


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

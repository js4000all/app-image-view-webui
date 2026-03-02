from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path

from app.models.schemas import DirectoryEntry, ImageEntry
from app.models.types import DirectoryId, DirectoryName, FileId
from app.repositories.filesystem import FileSystemRepository


class ServiceError(Exception):
    pass


class ResourceNotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class ValidationError(ServiceError):
    pass


class UnsupportedMediaTypeError(ServiceError):
    pass


class ResourceRegistry:
    """Thread-safe ID <-> path registry for directory_id/file_id resolution."""

    def __init__(self, *, roots: dict[str, Path] | None = None, base_dir: Path | None = None) -> None:
        if roots is None:
            if base_dir is None:
                raise ValueError("Either roots or base_dir is required")
            roots = {"d1": base_dir}

        self.roots = {key: path.resolve() for key, path in roots.items()}
        self._id_to_path: dict[str, Path] = {}
        self._path_to_id: dict[Path, str] = {}
        self._lock = threading.RLock()

    def _resolve_root(self, path: Path) -> tuple[str, Path]:
        resolved = path.resolve()
        for root_key, root_path in self.roots.items():
            if resolved == root_path or resolved.is_relative_to(root_path):
                return root_key, root_path
        first_key = next(iter(self.roots))
        return first_key, self.roots[first_key]

    def _directory_key_parts(self, directory_path: Path) -> tuple[str, str]:
        root_key, root_path = self._resolve_root(directory_path)
        try:
            relative = directory_path.resolve().relative_to(root_path)
            parts = relative.parts
            directory_name = parts[0] if parts else directory_path.name
        except ValueError:
            directory_name = directory_path.name
        return root_key, directory_name

    def _generate_directory_id(self, root_key: str, directory_name: str) -> str:
        seed = f"dir:v2:{root_key}:{directory_name}".encode("utf-8")
        return f"d_{blake2s(seed).hexdigest()}"

    def _generate_file_id(self, directory_id: str, file_name: str) -> str:
        seed = f"file:v2:{directory_id}:{file_name}".encode("utf-8")
        return f"f_{blake2s(seed).hexdigest()}"

    def register(self, path: Path, *, is_directory: bool | None = None) -> str:
        resolved_path = path.resolve()
        with self._lock:
            resource_id = self._path_to_id.get(resolved_path)
            if resource_id is not None:
                return resource_id

            resolved_is_directory = resolved_path.is_dir() if is_directory is None else is_directory
            if resolved_is_directory:
                root_key, directory_name = self._directory_key_parts(resolved_path)
                resource_id = self._generate_directory_id(root_key, directory_name)
            else:
                directory_id = self.register_directory(resolved_path.parent)
                resource_id = self._generate_file_id(directory_id, resolved_path.name)

            self._path_to_id[resolved_path] = resource_id
            self._id_to_path[resource_id] = resolved_path
            return resource_id

    def register_file(self, path: Path) -> str:
        return self.register(path, is_directory=False)

    def register_directory(self, path: Path) -> str:
        return self.register(path, is_directory=True)

    def get_directory_identity(self, directory_path: Path) -> tuple[str, str, str]:
        root_key, directory_name = self._directory_key_parts(directory_path)
        directory_id = self._generate_directory_id(root_key, directory_name)
        return directory_id, root_key, directory_name

    def discard(self, path: Path) -> None:
        resolved_path = path.resolve()
        with self._lock:
            resource_id = self._path_to_id.pop(resolved_path, None)
            if resource_id is not None:
                self._id_to_path.pop(resource_id, None)

    def resolve(
        self,
        resource_id: DirectoryId | FileId,
        *,
        base_dir: Path | None = None,
        expect_directory: bool,
    ) -> Path | None:
        with self._lock:
            path = self._id_to_path.get(resource_id)

        if path is None or not path.exists():
            if path is not None:
                self.discard(path)
            return None

        in_roots = any(path == root or path.is_relative_to(root) for root in self.roots.values())
        if not in_roots:
            self.discard(path)
            return None

        if base_dir is not None and not (path == base_dir or path.is_relative_to(base_dir)):
            return None
        if expect_directory and not path.is_dir():
            return None
        if not expect_directory and not path.is_file():
            return None
        return path


@dataclass
class ImageService:
    roots: dict[str, Path]
    repository: FileSystemRepository
    registry: ResourceRegistry

    def list_subdirectories(self) -> list[DirectoryEntry]:
        entries: list[DirectoryEntry] = []
        for root_key in self.roots:
            root_path = self.roots[root_key]
            subdirectories = self.repository.list_subdirectories(root_path)
            for path in subdirectories:
                directory_id, _, directory_name = self.registry.get_directory_identity(path)
                self.registry.register_directory(path)
                entries.append(DirectoryEntry(directory_id=directory_id, name=directory_name))
        return entries

    def list_images(self, directory_id: DirectoryId) -> tuple[Path, list[ImageEntry]]:
        directory = self.registry.resolve(directory_id, expect_directory=True)
        if directory is None:
            raise ResourceNotFoundError

        images = self.repository.list_images(directory)
        image_entries = [ImageEntry(file_id=self.registry.register_file(path), name=path.name) for path in images]
        return directory, image_entries

    def resolve_image(self, file_id: FileId) -> Path:
        file_path = self.registry.resolve(file_id, expect_directory=False)
        if file_path is None:
            raise ResourceNotFoundError
        if file_path.suffix.lower() not in self.repository.IMAGE_EXTENSIONS:
            raise UnsupportedMediaTypeError
        return file_path

    def get_image_metadata(self, file_id: FileId) -> tuple[DirectoryId, DirectoryName, ImageEntry]:
        file_path = self.resolve_image(file_id)
        directory_path = file_path.parent
        directory_id = self.registry.register_directory(directory_path)
        image_entry = ImageEntry(file_id=file_id, name=file_path.name)
        return directory_id, directory_path.name, image_entry

    def delete_image(self, file_id: FileId) -> Path:
        file_path = self.resolve_image(file_id)
        try:
            self.repository.delete_file(file_path)
        except OSError as exc:
            raise ServiceError from exc
        self.registry.discard(file_path)
        return file_path

    def rename_subdirectory(
        self, directory_id: DirectoryId, new_name: DirectoryName
    ) -> tuple[DirectoryId, DirectoryName, DirectoryName]:
        current_directory = self.registry.resolve(directory_id, expect_directory=True)
        if current_directory is None:
            raise ResourceNotFoundError

        stripped_name = new_name.strip()
        if not stripped_name or stripped_name in {".", ".."} or re.search(r"[\\/]", stripped_name):
            raise ValidationError

        root_key, root_path = self.registry._resolve_root(current_directory)
        destination = root_path / stripped_name
        if destination.exists():
            raise ConflictError

        try:
            self.repository.rename_directory(current_directory, destination)
        except OSError as exc:
            raise ServiceError from exc

        self.registry.discard(current_directory)
        new_directory_id = self.registry._generate_directory_id(root_key, stripped_name)
        self.registry.register_directory(destination)
        return new_directory_id, current_directory.name, stripped_name

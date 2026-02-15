from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.models.schemas import DirectoryEntry, ImageEntry
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

    def __init__(self) -> None:
        self._id_to_path: dict[str, Path] = {}
        self._path_to_id: dict[Path, str] = {}
        self._lock = threading.Lock()

    def register(self, path: Path) -> str:
        resolved_path = path.resolve()
        with self._lock:
            resource_id = self._path_to_id.get(resolved_path)
            if resource_id is None:
                resource_id = uuid4().hex
                self._path_to_id[resolved_path] = resource_id
                self._id_to_path[resource_id] = resolved_path
            return resource_id

    def discard(self, path: Path) -> None:
        resolved_path = path.resolve()
        with self._lock:
            resource_id = self._path_to_id.pop(resolved_path, None)
            if resource_id is not None:
                self._id_to_path.pop(resource_id, None)

    def resolve(self, resource_id: str, *, base_dir: Path, expect_directory: bool) -> Path | None:
        with self._lock:
            path = self._id_to_path.get(resource_id)

        if path is None:
            return None
        if not path.exists() or not path.is_relative_to(base_dir):
            self.discard(path)
            return None
        if expect_directory and not path.is_dir():
            return None
        if not expect_directory and not path.is_file():
            return None
        return path


@dataclass
class ImageService:
    base_dir: Path
    repository: FileSystemRepository
    registry: ResourceRegistry

    def list_subdirectories(self) -> list[DirectoryEntry]:
        subdirectories = self.repository.list_subdirectories(self.base_dir)
        return [DirectoryEntry(directory_id=self.registry.register(path), name=path.name) for path in subdirectories]

    def list_images(self, directory_id: str) -> tuple[Path, list[ImageEntry]]:
        directory = self.registry.resolve(directory_id, base_dir=self.base_dir, expect_directory=True)
        if directory is None:
            raise ResourceNotFoundError

        images = self.repository.list_images(directory)
        image_entries = [ImageEntry(file_id=self.registry.register(path), name=path.name) for path in images]
        return directory, image_entries

    def resolve_image(self, file_id: str) -> Path:
        file_path = self.registry.resolve(file_id, base_dir=self.base_dir, expect_directory=False)
        if file_path is None:
            raise ResourceNotFoundError
        if file_path.suffix.lower() not in self.repository.IMAGE_EXTENSIONS:
            raise UnsupportedMediaTypeError
        return file_path

    def delete_image(self, file_id: str) -> Path:
        file_path = self.resolve_image(file_id)
        try:
            self.repository.delete_file(file_path)
        except OSError as exc:
            raise ServiceError from exc
        self.registry.discard(file_path)
        return file_path

    def rename_subdirectory(self, directory_id: str, new_name: str) -> tuple[str, str, str]:
        current_directory = self.registry.resolve(directory_id, base_dir=self.base_dir, expect_directory=True)
        if current_directory is None:
            raise ResourceNotFoundError

        stripped_name = new_name.strip()
        if not stripped_name or stripped_name in {".", ".."} or re.search(r"[\\/]", stripped_name):
            raise ValidationError

        destination = self.base_dir / stripped_name
        if destination.exists():
            raise ConflictError

        try:
            self.repository.rename_directory(current_directory, destination)
        except OSError as exc:
            raise ServiceError from exc

        self.registry.discard(current_directory)
        new_directory_id = self.registry.register(destination)
        return new_directory_id, current_directory.name, stripped_name

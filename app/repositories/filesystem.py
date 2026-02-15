from __future__ import annotations

from pathlib import Path


class FileSystemRepository:
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}

    def list_subdirectories(self, base_dir: Path) -> list[Path]:
        return [entry for entry in sorted(base_dir.iterdir(), reverse=True) if entry.is_dir()]

    def list_images(self, directory: Path) -> list[Path]:
        return [
            entry
            for entry in sorted(directory.iterdir())
            if entry.is_file() and entry.suffix.lower() in self.IMAGE_EXTENSIONS
        ]

    def delete_file(self, path: Path) -> None:
        path.unlink()

    def rename_directory(self, source: Path, destination: Path) -> Path:
        source.rename(destination)
        return destination

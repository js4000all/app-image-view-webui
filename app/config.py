from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    base_dir: Path
    static_dir: Path

    @classmethod
    def from_paths(cls, *, base_dir: Path, static_dir: Path) -> "AppSettings":
        resolved_base = base_dir.expanduser().resolve()
        resolved_static = static_dir.expanduser().resolve()
        return cls(base_dir=resolved_base, static_dir=resolved_static)

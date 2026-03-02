from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict
from pydantic_settings_yaml import YamlBaseSettings


class RootEntry(BaseModel):
    path: Path


class PresetEntry(BaseModel):
    roots: dict[str, RootEntry] = Field(default_factory=dict)


class RootPresetsYaml(YamlBaseSettings):
    presets: dict[str, PresetEntry] = Field(default_factory=dict)
    model_config = SettingsConfigDict(yaml_file="root-presets.yaml")


@dataclass(frozen=True)
class AppSettings:
    preset_key: str
    roots: dict[str, Path]
    static_dir: Path
    db_path: Path

    @property
    def base_dir(self) -> Path:
        return next(iter(self.roots.values()))

    @classmethod
    def from_paths(cls, *, base_dir: Path, static_dir: Path) -> "AppSettings":
        resolved_base = base_dir.expanduser().resolve()
        resolved_static = static_dir.expanduser().resolve()
        return cls(
            preset_key="adhoc",
            roots={"d1": resolved_base},
            static_dir=resolved_static,
            db_path=Path("tag_index.sqlite3").resolve(),
        )

    @classmethod
    def from_preset(cls, *, preset_key: str, roots: dict[str, Path], static_dir: Path) -> "AppSettings":
        resolved_static = static_dir.expanduser().resolve()
        resolved_roots = {key: path.expanduser().resolve() for key, path in roots.items()}
        return cls(
            preset_key=preset_key,
            roots=resolved_roots,
            static_dir=resolved_static,
            db_path=Path(f"{preset_key}.sqlite3").resolve(),
        )


def load_root_presets(config_path: Path) -> dict[str, dict[str, Path]]:
    class _RootPresetsYaml(RootPresetsYaml):
        model_config = SettingsConfigDict(yaml_file=str(config_path))

    parsed = _RootPresetsYaml()
    result: dict[str, dict[str, Path]] = {}

    for preset_key, preset_entry in parsed.presets.items():
        if not preset_entry.roots:
            raise ValueError(f"Invalid preset '{preset_key}': roots must be a non-empty mapping")

        roots = {
            str(root_key): root_entry.path
            for root_key, root_entry in preset_entry.roots.items()
        }
        result[str(preset_key)] = roots

    return result

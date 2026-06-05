from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path
    data_dir: Path
    kg_dir: Path
    intermediate_dir: Path
    templates_dir: Path
    static_dir: Path
    schema_ttl: Path
    core_ttl: Path
    aligned_ttl: Path

    @classmethod
    def from_base_dir(cls, base_dir: Path) -> "AppConfig":
        data_dir = base_dir / "data"
        kg_dir = data_dir / "kg"
        intermediate_dir = data_dir / "intermediate"
        return cls(
            base_dir=base_dir,
            data_dir=data_dir,
            kg_dir=kg_dir,
            intermediate_dir=intermediate_dir,
            templates_dir=base_dir / "templates",
            static_dir=base_dir / "static",
            schema_ttl=kg_dir / "schema.ttl",
            core_ttl=kg_dir / "core.ttl",
            aligned_ttl=kg_dir / "aligned.ttl",
        )

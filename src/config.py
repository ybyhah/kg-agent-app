from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path
    data_dir: Path
    source_dir: Path
    kg_dir: Path
    intermediate_dir: Path
    docs_dir: Path
    templates_dir: Path
    static_dir: Path
    raw_text_dir: Path
    clean_text_dir: Path
    chapter_split_json: Path
    person_passages_json: Path
    entities_json: Path
    relations_json: Path
    extraction_prompts_md: Path
    evaluation_samples_json: Path
    schema_ttl: Path
    core_ttl: Path
    aligned_ttl: Path
    alignment_rules_md: Path
    sparql_examples_md: Path
    demo_script_md: Path
    team_interface_md: Path

    @classmethod
    def from_base_dir(cls, base_dir: Path) -> "AppConfig":
        data_dir = base_dir / "data"
        source_dir = data_dir / "source"
        kg_dir = data_dir / "kg"
        intermediate_dir = data_dir / "intermediate"
        docs_dir = base_dir / "docs"
        return cls(
            base_dir=base_dir,
            data_dir=data_dir,
            source_dir=source_dir,
            kg_dir=kg_dir,
            intermediate_dir=intermediate_dir,
            docs_dir=docs_dir,
            templates_dir=base_dir / "templates",
            static_dir=base_dir / "static",
            raw_text_dir=source_dir / "raw_text",
            clean_text_dir=source_dir / "clean_text",
            chapter_split_json=source_dir / "chapter_split.json",
            person_passages_json=source_dir / "person_passages.json",
            entities_json=intermediate_dir / "entities.json",
            relations_json=intermediate_dir / "relations.json",
            extraction_prompts_md=intermediate_dir / "extraction_prompts.md",
            evaluation_samples_json=intermediate_dir / "evaluation_samples.json",
            schema_ttl=kg_dir / "schema.ttl",
            core_ttl=kg_dir / "core.ttl",
            aligned_ttl=kg_dir / "aligned.ttl",
            alignment_rules_md=kg_dir / "alignment_rules.md",
            sparql_examples_md=data_dir / "examples" / "fewshot_sparql.md",
            demo_script_md=docs_dir / "demo_script.md",
            team_interface_md=docs_dir / "team_deliverables_interface.md",
        )

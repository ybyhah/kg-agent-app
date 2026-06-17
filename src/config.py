from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


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
    ontology_explanations_json: Path
    sparql_examples_md: Path
    demo_script_md: Path
    llm_mode: str
    llm_model_dir: Path | None
    llm_model_name: str
    llm_max_new_tokens: int
    llm_temperature: float
    llm_device: str
    llm_load_in_4bit: bool
    openai_api_key: str
    openai_base_url: str
    llm_reference_mode: bool

    @classmethod
    def from_base_dir(cls, base_dir: Path) -> "AppConfig":
        env_path = base_dir / ".env"
        env_example_path = base_dir / ".env.example"
        if env_path.exists():
            load_dotenv(env_path)
        elif env_example_path.exists():
            load_dotenv(env_example_path)

        data_dir = base_dir / "data"
        source_dir = data_dir / "source"
        kg_dir = data_dir / "kg"
        intermediate_dir = data_dir / "intermediate"
        docs_dir = base_dir / "docs"
        llm_mode = os.getenv("KG_AGENT_LLM_MODE", "disabled").strip() or "disabled"
        llm_model_dir_raw = os.getenv("KG_AGENT_LLM_MODEL_DIR", "").strip()
        llm_model_dir = Path(llm_model_dir_raw) if llm_model_dir_raw else None
        llm_model_name = os.getenv("KG_AGENT_OPENAI_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"
        deepseek_api_key_raw = os.getenv("DEEPSEEK_API_KEY", "").strip()
        openai_base_url = os.getenv("KG_AGENT_OPENAI_BASE_URL", "").strip() or os.getenv("OPENAI_BASE_URL", "").strip()
        if not openai_base_url and llm_model_name.lower().startswith("deepseek"):
            openai_base_url = "https://api.deepseek.com"
        openai_api_key = deepseek_api_key_raw

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
            ontology_explanations_json=kg_dir / "ontology_explanations.json",
            sparql_examples_md=data_dir / "examples" / "fewshot_sparql.md",
            demo_script_md=docs_dir / "demo_script.md",
            llm_mode=llm_mode,
            llm_model_dir=llm_model_dir,
            llm_model_name=llm_model_name,
            llm_max_new_tokens=int(os.getenv("KG_AGENT_LLM_MAX_NEW_TOKENS", "768")),
            llm_temperature=float(os.getenv("KG_AGENT_LLM_TEMPERATURE", "0.1")),
            llm_device=os.getenv("KG_AGENT_LLM_DEVICE", "auto").strip() or "auto",
            llm_load_in_4bit=os.getenv("KG_AGENT_LLM_LOAD_IN_4BIT", "0").strip() in {"1", "true", "True"},
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            llm_reference_mode=os.getenv("KG_AGENT_LLM_REFERENCE_MODE", "0").strip() in {"1", "true", "True"},
        )

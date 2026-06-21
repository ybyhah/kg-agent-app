#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.kg_alignment.align_entities import (  # noqa: E402
    ALIGNED_TTL,
    ENTITIES_JSON,
    KNOWN_CBDB_MAP,
    disambiguate,
    get_or_build_candidates,
    write_alignment_block,
)
from scripts.kg_alignment.ranked_backfill import (  # noqa: E402
    PERSON_TYPE,
    build_known_candidate,
    build_local_info,
    info_richness,
    resolve_seed_name,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "docs" / "kg_alignment" / "full_batch_gated_report.json"
WRITE_THRESHOLD = 0.85
REPORT_ONLY_THRESHOLD = 0.55
MIN_RICHNESS_TO_QUERY = 2


def _load_entities() -> list[dict[str, Any]]:
    payload = json.loads(ENTITIES_JSON.read_text(encoding="utf-8"))
    return payload.get("entities", [])


def _select_best_entities_by_name(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for entity in entities:
        if entity.get("type") != PERSON_TYPE:
            continue
        name = str(entity.get("name", "")).strip()
        if not name:
            continue
        seed_name = resolve_seed_name(name)
        entity_with_seed = dict(entity)
        entity_with_seed["alignment_seed_name"] = seed_name
        current = by_name.get(seed_name)
        if current is None:
            by_name[seed_name] = entity_with_seed
            continue
        current_priority = (info_richness(build_local_info(current.get("source_text", ""), name)), len(current.get("source_text", "") or ""))
        entity_priority = (info_richness(build_local_info(entity_with_seed.get("source_text", ""), name)), len(entity_with_seed.get("source_text", "") or ""))
        if entity_priority > current_priority:
            by_name[seed_name] = entity_with_seed
    return list(by_name.values())


def _record(entity: dict[str, Any], candidate: Any, rules: list[str], richness: int) -> dict[str, Any]:
    return {
        "name": entity.get("name", ""),
        "entity_id": entity.get("id", ""),
        "cbdb_id": candidate.external_id,
        "ctext_id": candidate.ctext_id,
        "match_score": candidate.match_score,
        "match_method": candidate.match_method,
        "alignment_status": candidate.alignment_status,
        "rules": rules,
        "richness": richness,
    }


def run_full_batch_gated(
    *,
    dry_run: bool = False,
    replace_existing: bool = True,
) -> dict[str, Any]:
    best_entities = _select_best_entities_by_name(_load_entities())
    written_records: list[dict[str, Any]] = []
    report_only_records: list[dict[str, Any]] = []
    skipped_records: list[dict[str, Any]] = []

    for entity in best_entities:
        name = entity.get("name", "")
        seed_name = str(entity.get("alignment_seed_name", "") or resolve_seed_name(name))
        entity_id = entity.get("id", "")
        local_info = build_local_info(entity.get("source_text", ""), name)
        local_info["id"] = entity_id
        richness = info_richness(local_info)

        if seed_name not in KNOWN_CBDB_MAP and richness < MIN_RICHNESS_TO_QUERY:
            skipped_records.append({"name": name, "seed_name": seed_name, "entity_id": entity_id, "reason": "insufficient_info", "richness": richness})
            continue

        candidates = [build_known_candidate(seed_name)] if seed_name in KNOWN_CBDB_MAP else get_or_build_candidates(name, local_info, skip_external=False)
        if not candidates:
            skipped_records.append({"name": name, "seed_name": seed_name, "entity_id": entity_id, "reason": "no_candidates", "richness": richness})
            continue

        best_candidate, rules = disambiguate(candidates, name, local_info)
        if best_candidate is None or best_candidate.alignment_status != "aligned":
            skipped_records.append({"name": name, "seed_name": seed_name, "entity_id": entity_id, "reason": "not_aligned", "richness": richness})
            continue

        record = _record(entity, best_candidate, rules, richness)
        record["seed_name"] = seed_name
        if best_candidate.match_score >= WRITE_THRESHOLD:
            write_alignment_block(
                ALIGNED_TTL,
                name,
                entity_id,
                best_candidate,
                replace_existing=replace_existing,
                dry_run=dry_run,
            )
            written_records.append(record)
        elif best_candidate.match_score >= REPORT_ONLY_THRESHOLD:
            report_only_records.append(record)
        else:
            skipped_records.append({"name": name, "entity_id": entity_id, "reason": "below_report_threshold", "richness": richness})

    summary = {
        "total_unique_names": len(best_entities),
        "written": len(written_records),
        "report_only": len(report_only_records),
        "skipped": len(skipped_records),
        "written_records": written_records,
        "report_only_records": report_only_records,
        "skipped_records": skipped_records,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    summary = run_full_batch_gated()
    print("=" * 68)
    print("全量人物批跑（高低阈值分流）")
    print("=" * 68)
    print(f"唯一人物名: {summary['total_unique_names']}")
    print(f"正式写回: {summary['written']}")
    print(f"仅入报告: {summary['report_only']}")
    print(f"跳过: {summary['skipped']}")
    print(f"报告文件: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

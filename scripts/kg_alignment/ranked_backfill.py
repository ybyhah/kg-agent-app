#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "docs" / "kg_alignment" / "ranked_backfill_top50_report.json"
PERSON_TYPE = "人物"
TOP_LIMIT = 50
WRITE_THRESHOLD = 0.55
REPORT_ONLY_THRESHOLD = 0.45

# 保守桥接：只收当前本地图谱中已确认出现、且几乎无歧义的固定写法差异。
SEED_NAME_BRIDGES: dict[str, tuple[str, ...]] = {
    "文徵明": ("文征明",),
    "释达受": ("达受",),
}


def _match_first(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def build_local_info(source_text: str, person_name: str) -> dict[str, Any]:
    text = (source_text or "").strip()
    info = {
        "字": _match_first(
            [r"字([\u4e00-\u9fff]{1,6})", r"一字([\u4e00-\u9fff]{1,6})", r"又字([\u4e00-\u9fff]{1,6})"],
            text,
        ),
        "号": _match_first(
            [r"号([\u4e00-\u9fff]{1,12})", r"别号([\u4e00-\u9fff]{1,12})", r"又号([\u4e00-\u9fff]{1,12})"],
            text,
        ),
        "籍贯": _match_first(
            [r"([\u4e00-\u9fff]{1,8})人", r"籍([\u4e00-\u9fff]{1,8})", r"居([\u4e00-\u9fff]{1,8})"],
            text,
        ),
        "朝代": _match_first([r"(明|清|元|宋|民国)人", r"(明|清|元|宋|民国)末"], text),
        "生年": _match_first([r"生于(\d{3,4})年", r"(\d{3,4})[-—至](\d{3,4})"], text),
        "卒年": _match_first([r"卒于(\d{3,4})年"], text),
        "谥号": "",
        "科举": _match_first([r"(进士|举人|贡生|诸生)"], text),
        "官职": _match_first(
            [r"官([\u4e00-\u9fff]{2,12})", r"授([\u4e00-\u9fff]{2,12})", r"历([\u4e00-\u9fff]{2,12})"],
            text,
        ),
        "source_text": text,
        "name": person_name,
    }

    year_range = re.search(r"(\d{3,4})[-—至](\d{3,4})", text)
    if year_range:
        info["生年"] = year_range.group(1)
        info["卒年"] = year_range.group(2)
    return info


def info_richness(local_info: dict[str, Any]) -> int:
    score = 0
    if local_info.get("字"):
        score += 2
    if local_info.get("号"):
        score += 2
    if local_info.get("籍贯"):
        score += 1
    if local_info.get("朝代"):
        score += 1
    if local_info.get("生年"):
        score += 1
    if local_info.get("卒年"):
        score += 1
    if local_info.get("科举"):
        score += 1
    if local_info.get("官职"):
        score += 1
    return score


def _entity_priority(entity: dict[str, Any]) -> tuple[int, int, float]:
    local_info = build_local_info(entity.get("source_text", ""), entity.get("name", ""))
    return (
        info_richness(local_info),
        len(entity.get("source_text", "") or ""),
        float(entity.get("confidence", 0.0) or 0.0),
    )


def _load_entities() -> list[dict[str, Any]]:
    payload = json.loads(ENTITIES_JSON.read_text(encoding="utf-8"))
    return payload.get("entities", [])


def resolve_seed_name(local_name: str) -> str:
    if local_name in KNOWN_CBDB_MAP:
        return local_name
    for seed_name, aliases in SEED_NAME_BRIDGES.items():
        if local_name == seed_name or local_name in aliases:
            return seed_name
    return local_name


def build_known_candidate(name: str) -> dict[str, Any]:
    known = KNOWN_CBDB_MAP[name]
    return {
        "cbdb_id": known["cbdb_id"],
        "name": name,
        "courtesy_name": known.get("courtesy_name", ""),
        "art_name": known.get("art_name", ""),
        "birth_year": known.get("birth_year", ""),
        "death_year": known.get("death_year", ""),
        "dynasty": known.get("dynasty", ""),
        "birth_place": known.get("birth_place", ""),
        "ctext_id": known.get("ctext_id", ""),
        "ctext_url": known.get("ctext_url", ""),
        "source": "KNOWN_MAP",
        "seed_match": True,
    }


def select_top_seed_entities(entities: list[dict[str, Any]], limit: int = TOP_LIMIT) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for entity in entities:
        if entity.get("type") != PERSON_TYPE:
            continue
        name = str(entity.get("name", "")).strip()
        if not name:
            continue
        seed_name = resolve_seed_name(name)
        if seed_name not in KNOWN_CBDB_MAP:
            continue
        entity_with_seed = dict(entity)
        entity_with_seed["alignment_seed_name"] = seed_name
        current = by_name.get(seed_name)
        if current is None or _entity_priority(entity_with_seed) > _entity_priority(current):
            by_name[seed_name] = entity_with_seed
    ranked = sorted(by_name.values(), key=_entity_priority, reverse=True)
    return ranked[:limit]


def _record_from_candidate(entity: dict[str, Any], candidate: Any, rules: list[str], richness: int) -> dict[str, Any]:
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


def run_ranked_backfill(
    limit: int = TOP_LIMIT,
    *,
    dry_run: bool = False,
    replace_existing: bool = True,
    write_threshold: float = WRITE_THRESHOLD,
    report_only_threshold: float = REPORT_ONLY_THRESHOLD,
) -> dict[str, Any]:
    selected_entities = select_top_seed_entities(_load_entities(), limit=limit)
    written_records: list[dict[str, Any]] = []
    report_only_records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for entity in selected_entities:
        name = entity.get("name", "")
        seed_name = str(entity.get("alignment_seed_name", "") or resolve_seed_name(name))
        entity_id = entity.get("id", "")
        local_info = build_local_info(entity.get("source_text", ""), name)
        local_info["id"] = entity_id
        richness = info_richness(local_info)

        candidates = [build_known_candidate(seed_name)] if seed_name in KNOWN_CBDB_MAP else get_or_build_candidates(name, local_info, skip_external=False)
        if not candidates:
            skipped.append(
                {
                    "name": name,
                    "seed_name": seed_name,
                    "entity_id": entity_id,
                    "reason": "no_candidates",
                    "richness": richness,
                }
            )
            continue

        best_candidate, rules = disambiguate(candidates, name, local_info)
        if best_candidate is None or best_candidate.alignment_status != "aligned":
            skipped.append(
                {
                    "name": name,
                    "seed_name": seed_name,
                    "entity_id": entity_id,
                    "reason": "not_aligned",
                    "richness": richness,
                }
            )
            continue

        record = _record_from_candidate(entity, best_candidate, rules, richness)
        record["seed_name"] = seed_name
        if best_candidate.match_score >= write_threshold:
            write_alignment_block(
                ALIGNED_TTL,
                name,
                entity_id,
                best_candidate,
                replace_existing=replace_existing,
                dry_run=dry_run,
            )
            written_records.append(record)
        elif best_candidate.match_score >= report_only_threshold:
            report_only_records.append(record)
        else:
            skipped.append({"name": name, "entity_id": entity_id, "reason": "below_report_threshold", "richness": richness})

    summary = {
        "selected_targets": len(selected_entities),
        "written": len(written_records),
        "report_only": len(report_only_records),
        "skipped": len(skipped),
        "written_records": written_records,
        "report_only_records": report_only_records,
        "skipped_records": skipped,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    summary = run_ranked_backfill()
    print("=" * 68)
    print("Top50 高信息人物正式回填")
    print("=" * 68)
    print(f"选中目标: {summary['selected_targets']}")
    print(f"正式写回: {summary['written']}")
    print(f"仅入报告: {summary['report_only']}")
    print(f"跳过: {summary['skipped']}")
    print(f"报告文件: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高信息人物正式回填脚本。

目标：
1. 从 entities.json 中挑出一组高信息、可确认的人物实体；
2. 走当前 v7 对齐与消歧逻辑；
3. 将结果正式写回 data/kg/aligned.ttl；
4. 对同一 source entity id 使用覆盖式写回，避免重复堆叠旧块。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.kg_alignment.align_entities import (
    ALIGNED_TTL,
    ENTITIES_JSON,
    disambiguate,
    extract_person_info,
    get_or_build_candidates,
    write_alignment_block,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "docs" / "kg_alignment" / "formal_backfill_report.json"

# 这批人物已经过前序实跑验证，适合先做正式回填。
CURATED_TARGET_NAMES = [
    "文彭",
    "文征明",
    "何震",
    "许友",
    "周亮工",
    "丁敬",
    "郑燮",
    "金农",
    "吴大澂",
    "邓石如",
    "赵之谦",
]


def _load_entities() -> list[dict[str, Any]]:
    payload = json.loads(ENTITIES_JSON.read_text(encoding="utf-8"))
    return payload.get("entities", [])


def _score_entity_record(entity: dict[str, Any]) -> tuple[int, int]:
    source_text = entity.get("source_text", "") or ""
    info = extract_person_info(source_text, entity.get("name", ""))
    richness = sum(
        1
        for key in ("字", "号", "籍贯", "朝代", "生年", "卒年")
        if info.get(key)
    )
    return richness, len(source_text)


def _pick_best_entity(name: str, entities: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        entity
        for entity in entities
        if entity.get("type") == "人物" and entity.get("name") == name
    ]
    if not candidates:
        return None
    return max(candidates, key=_score_entity_record)


def _build_target_entities(target_names: list[str], entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for name in target_names:
        entity = _pick_best_entity(name, entities)
        if not entity:
            continue
        entity_id = str(entity.get("id", "")).strip()
        if not entity_id or entity_id in seen_ids:
            continue
        seen_ids.add(entity_id)
        selected.append(entity)
    return selected


def run_formal_backfill(
    target_names: list[str] | None = None,
    *,
    dry_run: bool = False,
    replace_existing: bool = True,
    skip_external: bool = False,
) -> dict[str, Any]:
    target_names = target_names or CURATED_TARGET_NAMES
    entities = _load_entities()
    selected_entities = _build_target_entities(target_names, entities)

    records: list[dict[str, Any]] = []
    written = 0
    with_cbdb = 0
    with_ctext = 0
    skipped: list[dict[str, str]] = []

    for entity in selected_entities:
        name = entity.get("name", "")
        entity_id = entity.get("id", "")
        source_text = entity.get("source_text", "") or ""

        local_info = extract_person_info(source_text, name)
        local_info["id"] = entity_id

        candidates = get_or_build_candidates(name, local_info, skip_external=skip_external)
        if not candidates:
            skipped.append({"name": name, "id": entity_id, "reason": "no_candidates"})
            continue

        best_candidate, rules = disambiguate(candidates, name, local_info)
        if best_candidate is None or best_candidate.alignment_status != "aligned":
            skipped.append({"name": name, "id": entity_id, "reason": "not_aligned"})
            continue

        write_alignment_block(
            ALIGNED_TTL,
            name,
            entity_id,
            best_candidate,
            replace_existing=replace_existing,
            dry_run=dry_run,
        )

        written += 1
        if best_candidate.external_id:
            with_cbdb += 1
        if best_candidate.ctext_id:
            with_ctext += 1

        records.append(
            {
                "name": name,
                "entity_id": entity_id,
                "cbdb_id": best_candidate.external_id,
                "ctext_id": best_candidate.ctext_id,
                "match_score": best_candidate.match_score,
                "match_method": best_candidate.match_method,
                "alignment_status": best_candidate.alignment_status,
                "rules": rules,
            }
        )

    summary = {
        "selected_targets": len(selected_entities),
        "written": written,
        "with_cbdb": with_cbdb,
        "with_ctext": with_ctext,
        "skipped": skipped,
        "records": records,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    summary = run_formal_backfill()
    print("=" * 68)
    print("高信息人物正式回填")
    print("=" * 68)
    print(f"选中目标: {summary['selected_targets']}")
    print(f"正式写回: {summary['written']}")
    print(f"写入 cbdbId: {summary['with_cbdb']}")
    print(f"写入 ctextId: {summary['with_ctext']}")
    print(f"报告文件: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

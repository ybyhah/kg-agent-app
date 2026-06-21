#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量实体对齐 v7 - LLM 增强版

流程：
1. 读取本地人物实体
2. 用本地文本提取字号、籍贯、朝代、生卒年等线索
3. 规则高分人物优先对齐
4. 中分人物检索真实外部候选后交给 LLM 二次打分
5. 将高置信结果写回 aligned.ttl 与统计报告
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.kg_alignment.align_entities import (
    AlignmentCandidate,
    append_to_aligned_ttl,
    disambiguate,
    extract_person_info,
    get_or_build_candidates,
    llm_disambiguation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTITIES_JSON = PROJECT_ROOT / "data" / "intermediate" / "entities.json"
ALIGNED_TTL = PROJECT_ROOT / "data" / "kg" / "aligned.ttl"
REPORT_PATH = PROJECT_ROOT / "docs" / "kg_alignment" / "alignment_report_v7.txt"

RULE_HIGH_THRESHOLD = 0.30
RULE_LLM_THRESHOLD = 0.15
LLM_HIGH_THRESHOLD = 50
MAX_LLM_CALLS = 100
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def is_valid_name(name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 8:
        return False
    if any(ch in name for ch in "。，,！？?；;：:、（）()[]{}0123456789"):
        return False
    return True


def extract_enhanced(source_text: str, person_name: str) -> dict[str, Any]:
    info = extract_person_info(source_text, person_name)
    info["_raw_text"] = source_text or ""
    return info


def enhanced_score(info: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if info.get("字"):
        score += 0.30
        reasons.append("字")
    if info.get("号"):
        score += 0.20
        reasons.append("号")
    if info.get("籍贯"):
        score += 0.15
        reasons.append("籍贯")
    if info.get("朝代"):
        score += 0.15
        reasons.append("朝代")
    if info.get("生年"):
        score += 0.15
        reasons.append("生年")
    if info.get("卒年"):
        score += 0.10
        reasons.append("卒年")
    return score, reasons


def _candidate_to_dict(
    candidate: AlignmentCandidate,
    *,
    method: str,
    local_name: str,
    source_id: str,
    local_info: dict[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "name": local_name,
        "source_id": source_id,
        "candidate": candidate,
        "method": method,
        "info": local_info,
        "reasons": reasons,
        "rule_score": candidate.match_score,
        "llm_score": candidate.llm_score,
        "llm_reason": candidate.llm_reason,
    }


def _write_alignment_result(result: dict[str, Any]) -> None:
    append_to_aligned_ttl(
        result["name"],
        result["source_id"],
        result["candidate"],
        dry_run=False,
    )


def _build_report(
    total: int,
    aligned_rule: list[dict[str, Any]],
    aligned_llm: list[dict[str, Any]],
    insufficient: list[dict[str, Any]],
    need_llm_count: int,
    llm_call_count: int,
) -> str:
    return f"""实体对齐报告 v7 (LLM 增强版)
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

统计:
- 总实体数: {total}
- 规则直接对齐: {len(aligned_rule)}
- 进入 LLM 候选池: {need_llm_count}
- LLM 辅助对齐: {len(aligned_llm)}
- LLM 调用次数: {llm_call_count}
- 数据不足/未对齐: {len(insufficient)}
- 总计对齐: {len(aligned_rule) + len(aligned_llm)}

配置:
- 规则高分阈值: {RULE_HIGH_THRESHOLD}
- LLM 调用阈值: {RULE_LLM_THRESHOLD}
- LLM 通过阈值: {LLM_HIGH_THRESHOLD}
- 最大 LLM 调用次数: {MAX_LLM_CALLS}

说明:
- llm_disambiguation: 使用真实外部候选进行二次打分
- 写回字段: owl:sameAs / cbdbId / alignmentStatus / alignmentMethod / llmScore / llmReason
"""


def run_batch_alignment() -> dict[str, int]:
    with open(ENTITIES_JSON, "r", encoding="utf-8") as f:
        payload = json.load(f)

    entities = payload.get("entities", [])
    total = len(entities)

    aligned_rule: list[dict[str, Any]] = []
    aligned_llm: list[dict[str, Any]] = []
    insufficient: list[dict[str, Any]] = []
    need_llm_count = 0
    llm_call_count = 0

    for entity in entities:
        name = entity.get("name", "")
        source_text = entity.get("source_text", "") or ""
        source_id = entity.get("id", name)

        if not is_valid_name(name):
            continue

        info = extract_enhanced(source_text, name)
        score, reasons = enhanced_score(info)

        if score >= RULE_HIGH_THRESHOLD:
            candidates = get_or_build_candidates(name, info, skip_external=False)
            best_candidate, best_rules = disambiguate(candidates, name, info)
            if best_candidate and best_candidate.alignment_status == "aligned":
                best_candidate.match_score = max(best_candidate.match_score, score)
                best_candidate.match_method = "rule_based"
                aligned_rule.append(
                    _candidate_to_dict(
                        best_candidate,
                        method="rule",
                        local_name=name,
                        source_id=source_id,
                        local_info=info,
                        reasons=best_rules or reasons,
                    )
                )
                continue

        if score >= RULE_LLM_THRESHOLD and llm_call_count < MAX_LLM_CALLS:
            candidates = get_or_build_candidates(name, info, skip_external=False)
            best_candidate, best_rules = disambiguate(candidates, name, info)
            need_llm_count += 1

            if best_candidate is None:
                insufficient.append({"name": name, "reason": "无候选"})
                continue

            llm_call_count += 1
            llm_candidates = llm_disambiguation(
                person_name=name,
                local_info=info,
                candidates=[best_candidate],
                api_key=LLM_API_KEY,
            )

            if (
                llm_candidates
                and llm_candidates[0].llm_score is not None
                and llm_candidates[0].llm_score >= LLM_HIGH_THRESHOLD
            ):
                final_candidate = llm_candidates[0]
                final_candidate.alignment_status = "aligned"
                final_candidate.match_method = "llm_disambiguation"
                aligned_llm.append(
                    _candidate_to_dict(
                        final_candidate,
                        method="llm",
                        local_name=name,
                        source_id=source_id,
                        local_info=info,
                        reasons=best_rules or reasons,
                    )
                )
            else:
                insufficient.append({"name": name, "reason": "LLM 未通过阈值"})
            continue

        insufficient.append({"name": name, "reason": "数据不足"})

    for result in aligned_rule + aligned_llm:
        _write_alignment_result(result)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        _build_report(
            total=total,
            aligned_rule=aligned_rule,
            aligned_llm=aligned_llm,
            insufficient=insufficient,
            need_llm_count=need_llm_count,
            llm_call_count=llm_call_count,
        ),
        encoding="utf-8",
    )

    return {
        "total": total,
        "aligned_rule": len(aligned_rule),
        "aligned_llm": len(aligned_llm),
        "insufficient": len(insufficient),
        "need_llm_count": need_llm_count,
        "llm_calls": llm_call_count,
    }


def main() -> int:
    summary = run_batch_alignment()
    print("=" * 70)
    print("批量实体对齐 v7 - LLM 增强版")
    print("=" * 70)
    print(f"总实体数: {summary['total']}")
    print(f"规则对齐: {summary['aligned_rule']}")
    print(f"LLM 对齐: {summary['aligned_llm']}")
    print(f"LLM 调用: {summary['llm_calls']}")
    print(f"未对齐/数据不足: {summary['insufficient']}")
    print(f"报告文件: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

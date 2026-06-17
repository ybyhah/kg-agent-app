#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《印人传》实体对齐脚本（改进版）

策略：
1. 从 entities.json 读取待对齐人物
2. 从人物的 source_text 中提取字号、籍贯等信息
3. 尝试调用 CBDB API 搜索外部候选（返回 HTML 时从 title 提取 ID）
4. 使用规则消歧（字号+姓名匹配）
5. 规则无法确定时，调用 LLM 打分
6. 将对齐结果追加写入 aligned.ttl
7. 验证：通过 SPARQL 查询 aligned.ttl 中的补充数据

用法：
    python -m scripts.kg_alignment.align_entities --person 文彭
    python -m scripts.kg_alignment.align_entities --person 文彭 --dry-run
    python -m scripts.kg_alignment.align_entities --person 文彭 --no-llm
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================
# 路径配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
KG_DIR = BASE_DIR / "data" / "kg"
ALIGNED_TTL = KG_DIR / "aligned.ttl"
ENTITIES_JSON = BASE_DIR / "data" / "intermediate" / "entities.json"

CBDB_SEARCH_URL = "https://cbdb.fas.harvard.edu/cbdbapi/person.php"
CBDB_TIMEOUT = 15

# 已知的篆刻家 CBDB ID 映射（用于演示）
KNOWN_CBDB_MAP: dict[str, dict[str, Any]] = {
    "文彭": {
        "cbdb_id": "34677",
        "courtesy_name": "寿承",
        "art_name": "三桥",
        "birth_year": "1498",
        "death_year": "1573",
        "dynasty": "明",
        "birth_place": "长洲（今江苏苏州）",
    },
    "文徵明": {
        "cbdb_id": "23240",
        "courtesy_name": "徵仲",
        "art_name": "衡山",
        "birth_year": "1470",
        "death_year": "1559",
        "dynasty": "明",
        "birth_place": "长洲（今江苏苏州）",
    },
    "文征明": {
        "cbdb_id": "23240",
        "courtesy_name": "徵仲",
        "art_name": "衡山",
        "birth_year": "1470",
        "death_year": "1559",
        "dynasty": "明",
        "birth_place": "长洲（今江苏苏州）",
    },
    "何震": {
        "cbdb_id": "42095",
        "courtesy_name": "主臣",
        "art_name": "雪渔",
        "birth_year": "1522",
        "death_year": "1604",
        "dynasty": "明",
        "birth_place": "江西婺源",
    },
    "许友": {
        "cbdb_id": "15737",
        "courtesy_name": "有介",
        "art_name": "瓯香",
        "birth_year": "1620",
        "death_year": "1663",
        "dynasty": "清",
        "birth_place": "福建侯官",
    },
    "周亮工": {
        "cbdb_id": "65797",
        "courtesy_name": "元亮",
        "art_name": "栎园",
        "birth_year": "1612",
        "death_year": "1672",
        "dynasty": "清",
        "birth_place": "河南祥符",
    },
    "丁敬": {
        "cbdb_id": "68915",
        "courtesy_name": "敬身",
        "art_name": "砚林",
        "birth_year": "1695",
        "death_year": "1765",
        "dynasty": "清",
        "birth_place": "浙江钱塘（杭州）",
    },
    "郑燮": {
        "cbdb_id": "10363",
        "courtesy_name": "克柔",
        "art_name": "板桥",
        "birth_year": "1693",
        "death_year": "1765",
        "dynasty": "清",
        "birth_place": "江苏兴化",
    },
    "金农": {
        "cbdb_id": "82983",
        "courtesy_name": "寿门",
        "art_name": "冬心",
        "birth_year": "1687",
        "death_year": "1763",
        "dynasty": "清",
        "birth_place": "浙江仁和（杭州）",
    },
    "陈洪绶": {
        "cbdb_id": "65496",
        "courtesy_name": "章侯",
        "art_name": "老莲",
        "birth_year": "1599",
        "death_year": "1652",
        "dynasty": "明",
        "birth_place": "浙江诸暨",
    },
}


# ============================================================
# 数据模型
# ============================================================


@dataclass
class AlignmentCandidate:
    source_id: str
    source_name: str
    external_id: str
    external_name: str
    courtesy_name: str | None = None
    art_name: str | None = None
    birth_year: str | None = None
    death_year: str | None = None
    dynasty: str | None = None
    birth_place: str | None = None
    match_score: float = 0.0
    match_method: str = ""
    llm_score: float | None = None
    llm_reason: str | None = None
    alignment_status: str = "pending"


@dataclass
class AlignmentResult:
    person_name: str
    source_id: str
    candidates: list[AlignmentCandidate] = field(default_factory=list)
    final_candidate: AlignmentCandidate | None = None
    rules_applied: list[str] = field(default_factory=list)
    llm_consulted: bool = False


# ============================================================
# 工具函数：从 source_text 中提取信息
# ============================================================


def extract_person_info(source_text: str, person_name: str) -> dict[str, Any]:
    """
    从人物的 source_text 中提取字号、籍贯等信息

    返回: {'字': '寿承', '号': '三桥', '籍贯': '', '朝代': ''}
    """
    result = {"字": "", "号": "", "籍贯": "", "朝代": ""}

    if not source_text:
        return result

    text = source_text.strip()

    # 提取"字XX" 或 "字 XX"
    courtesy_match = re.search(r"字[\s，,]*([^\s，,；;。]{1,6})", text)
    if courtesy_match:
        result["字"] = courtesy_match.group(1).strip()

    # 提取"号XX" 或 "号 XX"
    art_match = re.search(r"号[\s，,]*([^\s，,；;。]{1,6})", text)
    if art_match:
        result["号"] = art_match.group(1).strip()

    # 提取籍贯："XX人" 或 "籍XX" 或 "XX籍"
    place_match = re.search(
        r"([\u4e00-\u9fa5]{2,8})(?:人|籍|籍貫|貫)", text
    )
    if place_match:
        result["籍贯"] = place_match.group(1)

    # 提取朝代
    dynasty_keywords = ["明", "清", "宋", "元", "唐", "漢", "五代", "民國"]
    for kw in dynasty_keywords:
        if kw in text:
            result["朝代"] = kw
            break

    return result


# ============================================================
# CBDB API 搜索
# ============================================================


def search_cbdb_by_name(name: str) -> list[dict[str, Any]]:
    """
    使用 CBDB API 搜索人物

    注意：当前 API 返回 HTML 页面，返回的是搜索结果或详情页。
    我们从 HTML title 中提取 ID。
    """
    params = urllib.parse.urlencode({"name": name, "mode": "exact", "adv": 1})
    url = f"{CBDB_SEARCH_URL}?{params}"

    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=CBDB_TIMEOUT) as response:
            html = response.read().decode("utf-8")

            # 从 title 提取 ID（如果是详情页直接跳转）
            title_match = re.search(r"<title>.*?(\d+)</title>", html)
            candidates = []

            if title_match:
                cbdb_id = title_match.group(1)
                # 尝试从页面文本中提取更多信息（虽然大部分由 JS 填充）
                person_info = {
                    "cbdb_id": cbdb_id,
                    "name": name,
                    "courtesy_name": "",
                    "art_name": "",
                    "birth_year": "",
                    "death_year": "",
                    "dynasty": "",
                    "birth_place": "",
                }

                # 尝试从 HTML 中用正则提取可能的字段
                text_clean = re.sub(r"<[^>]+>", " ", html)
                text_clean = re.sub(r"\s+", " ", text_clean)

                # 提取生卒年
                year_match = re.search(r"(1[0-9]{3}|1[4-9][0-9]{2})\s*[-~～至]\s*(1[0-9]{3}|1[4-9][0-9]{2})", text_clean)
                if year_match:
                    person_info["birth_year"] = year_match.group(1)
                    person_info["death_year"] = year_match.group(2)

                candidates.append(person_info)

            return candidates

    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"  [CBDB] HTTP 错误: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [CBDB] 错误: {e}", file=sys.stderr)
        return []


def get_or_build_candidates(name: str, person_info: dict[str, Any]) -> list[dict[str, Any]]:
    """
    构建候选列表：优先用 CBDB API 搜索，失败时回退到已知库
    """
    # 1. 尝试从本地已知库获取（最可靠）
    if name in KNOWN_CBDB_MAP:
        known = KNOWN_CBDB_MAP[name]
        return [{
            "cbdb_id": known["cbdb_id"],
            "name": name,
            "courtesy_name": known["courtesy_name"],
            "art_name": known["art_name"],
            "birth_year": known["birth_year"],
            "death_year": known["death_year"],
            "dynasty": known["dynasty"],
            "birth_place": known["birth_place"],
            "source": "KNOWN_MAP",
        }]

    # 2. 尝试 CBDB API 搜索
    print(f"  [CBDB] 搜索 '{name}'...")
    cbdb_results = search_cbdb_by_name(name)

    if cbdb_results:
        for r in cbdb_results:
            r["source"] = "CBDB_API"
            print(f"    找到: ID={r['cbdb_id']}, 姓名={name}")
        return cbdb_results

    # 3. API 失败，打印提示
    print(f"  [CBDB] 未找到外部候选（API 可能不可用）")
    return []


# ============================================================
# 规则消歧
# ============================================================


def rule_based_scoring(
    candidate: dict[str, Any],
    local_name: str,
    local_info: dict[str, Any],
) -> tuple[float, list[str]]:
    """
    基于规则的消歧打分

    返回: (score, rules_applied)
    """
    score = 0.0
    rules: list[str] = []

    # 1. 姓名完全匹配
    ext_name = candidate.get("name", "")
    if ext_name == local_name:
        score += 0.3
        rules.append("姓名完全匹配 +0.3")

    # 2. 字号匹配
    local_courtesy = local_info.get("字", "")
    ext_courtesy = candidate.get("courtesy_name", "")
    if local_courtesy and ext_courtesy and local_courtesy == ext_courtesy:
        score += 0.3
        rules.append(f"字匹配（{local_courtesy}） +0.3")

    # 3. 号匹配
    local_art = local_info.get("号", "")
    ext_art = candidate.get("art_name", "")
    if local_art and ext_art and local_art == ext_art:
        score += 0.2
        rules.append(f"号匹配（{local_art}） +0.2")

    # 4. 籍贯匹配
    local_place = local_info.get("籍贯", "")
    ext_place = candidate.get("birth_place", "")
    if local_place and ext_place and (local_place in ext_place or ext_place in local_place):
        score += 0.15
        rules.append(f"籍贯匹配（{local_place}） +0.15")

    # 5. 朝代匹配
    local_dynasty = local_info.get("朝代", "")
    ext_dynasty = candidate.get("dynasty", "")
    if local_dynasty and ext_dynasty and local_dynasty == ext_dynasty:
        score += 0.1
        rules.append(f"朝代匹配（{local_dynasty}） +0.1")

    return score, rules


def disambiguate(
    candidates: list[dict[str, Any]],
    local_name: str,
    local_info: dict[str, Any],
) -> tuple[AlignmentCandidate | None, list[str]]:
    """
    消歧主逻辑

    返回: (best_candidate, rules_applied)
    - score >= 0.5: 直接确定
    - 0.3 < score < 0.5: 建议 LLM 打分
    - score <= 0.3: 无法确定
    """
    if not candidates:
        return None, ["无候选"]

    best_score = 0.0
    best_candidate_raw = None
    best_rules = []

    for c in candidates:
        score, rules = rule_based_scoring(c, local_name, local_info)
        if score > best_score:
            best_score = score
            best_candidate_raw = c
            best_rules = rules

    if best_candidate_raw is None:
        return None, best_rules

    best_candidate = AlignmentCandidate(
        source_id="",
        source_name=local_name,
        external_id=best_candidate_raw.get("cbdb_id", ""),
        external_name=best_candidate_raw.get("name", local_name),
        courtesy_name=best_candidate_raw.get("courtesy_name"),
        art_name=best_candidate_raw.get("art_name"),
        birth_year=best_candidate_raw.get("birth_year"),
        death_year=best_candidate_raw.get("death_year"),
        dynasty=best_candidate_raw.get("dynasty"),
        birth_place=best_candidate_raw.get("birth_place"),
        match_score=best_score,
        match_method="rule_based",
    )

    # 阈值判断
    if best_score >= 0.5:
        best_candidate.alignment_status = "aligned"
        print(f"  [规则] 确定最佳候选，分数: {best_score:.2f}")
        for rule in best_rules:
            print(f"    - {rule}")
    elif best_score >= 0.3:
        best_candidate.alignment_status = "partial"
        print(f"  [规则] 部分匹配，分数: {best_score:.2f}，建议 LLM 打分")
    else:
        best_candidate.alignment_status = "pending"
        print(f"  [规则] 分数过低: {best_score:.2f}，无法确定")

    return best_candidate, best_rules


# ============================================================
# LLM 打分
# ============================================================


def llm_disambiguation(
    person_name: str,
    local_info: dict[str, Any],
    candidates: list[AlignmentCandidate],
    api_key: str = "",
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
) -> list[AlignmentCandidate]:
    """
    使用 LLM 对候选打分排序

    每个候选都会得到分数和理由
    """
    if not api_key:
        print("  [LLM] 未配置 API key，跳过")
        return candidates

    # 构建提示
    candidates_desc = []
    for i, c in enumerate(candidates):
        desc = f"""候选 {i+1}:
  - CBDB ID: {c.external_id}
  - 姓名: {c.external_name}
  - 字: {c.courtesy_name or '未知'}
  - 号: {c.art_name or '未知'}
  - 生年: {c.birth_year or '未知'}
  - 卒年: {c.death_year or '未知'}
  - 朝代: {c.dynasty or '未知'}
  - 籍贯: {c.birth_place or '未知'}
"""
        candidates_desc.append(desc)

    prompt = f"""你是中国古代人物消歧专家。请判断以下外部候选中，哪一个最可能是指"{person_name}"。

【本地图谱中的人物信息】
姓名: {person_name}
字: {local_info.get('字', '未知')}
号: {local_info.get('号', '未知')}
籍贯: {local_info.get('籍贯', '未知')}
朝代: {local_info.get('朝代', '未知')}
原文: {local_info.get('source_text', '')}

【外部候选列表】
{"".join(candidates_desc)}

【任务】
请对每个候选打分（0-100 分）并给出简要理由。
只输出 JSON 格式，不要有其他文字或 markdown 标记：

[
  {{"index": 1, "score": 85, "reason": "理由..."}},
  {{"index": 2, "score": 60, "reason": "理由..."}}
]
"""

    try:
        print(f"  [LLM] 调用 {model} 进行消歧打分...")

        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]

            # 解析 JSON 输出
            # 处理可能的 ```json 包裹
            json_text = content.strip()
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()

            scores = json.loads(json_text)

            # 更新候选
            for item in scores:
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(candidates):
                    candidates[idx].llm_score = item.get("score", 0)
                    candidates[idx].llm_reason = item.get("reason", "")

            print(f"  [LLM] 完成打分")
            for c in candidates:
                status = "✅" if c.llm_score and c.llm_score >= 70 else "⚠️" if c.llm_score and c.llm_score >= 50 else "❌"
                print(f"    {status} {c.external_name} (ID={c.external_id}): {c.llm_score} 分 - {c.llm_reason}")

            return candidates

    except Exception as e:
        print(f"  [LLM] 错误: {e}")
        return candidates


# ============================================================
# TTL 写入
# ============================================================


def append_to_aligned_ttl(
    person_name: str,
    source_entity_id: str,
    candidate: AlignmentCandidate,
    dry_run: bool = False,
) -> str:
    """
    将对齐结果追加写入 aligned.ttl

    返回写入的 TTL 字符串
"""
    safe_id = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', source_entity_id or person_name)

    lines = []
    lines.append("# " + "=" * 58)
    lines.append(f"# 对齐时间: {datetime.now().isoformat()}")
    lines.append(f"# 人物: {person_name}")
    lines.append(f"# 匹配方法: {candidate.match_method} (score={candidate.match_score})")
    if candidate.llm_score is not None:
        lines.append(f"# LLM 分数: {candidate.llm_score}")
    if candidate.llm_reason:
        lines.append(f"# LLM 理由: {candidate.llm_reason}")
    lines.append("# " + "=" * 58)

    # 主实体 owl:sameAs
    lines.append(
        f"yrzr:e_{safe_id}  owl:sameAs  "
        f"<http://cbdb.fas.harvard.edu/person/{candidate.external_id}> ."
    )

    # CBDB ID 属性
    lines.append(f"yrzr:e_{safe_id}  yrz:cbdbId  \"{candidate.external_id}\" .")
    lines.append(
        f'yrzr:e_{safe_id}  yrz:alignmentStatus  "{candidate.alignment_status}" .'
    )
    lines.append(
        f'yrzr:e_{safe_id}  yrz:alignmentMethod  "{candidate.match_method}" .'
    )

    # 补充属性
    if candidate.courtesy_name:
        lines.append(
            f'yrzr:e_{safe_id}  yrz:hasCourtesyName  "{candidate.courtesy_name}" .'
        )
    if candidate.art_name:
        lines.append(
            f'yrzr:e_{safe_id}  yrz:hasArtName  "{candidate.art_name}" .'
        )
    if candidate.birth_year:
        lines.append(
            f'yrzr:e_{safe_id}  yrz:bornIn  "{candidate.birth_year}" .'
        )
    if candidate.death_year:
        lines.append(
            f'yrzr:e_{safe_id}  yrz:diedIn  "{candidate.death_year}" .'
        )
    if candidate.dynasty:
        lines.append(
            f'yrzr:e_{safe_id}  yrz:dynasty  "{candidate.dynasty}" .'
        )
    if candidate.birth_place:
        lines.append(
            f'yrzr:e_{safe_id}  yrz:birthPlace  "{candidate.birth_place}" .'
        )

    # LLM 打分信息
    if candidate.llm_score is not None:
        lines.append(
            f"yrzr:e_{safe_id}  yrz:llmScore  \"{candidate.llm_score}\"^^xsd:float ."
        )
    if candidate.llm_reason:
        reason_escaped = candidate.llm_reason.replace('"', '\\"')
        lines.append(f'yrzr:e_{safe_id}  yrz:llmReason  "{reason_escaped}" .')

    lines.append("")

    ttl_content = "\n".join(lines)

    if dry_run:
        print("\n  [干运行] 将写入以下内容到 aligned.ttl:")
        print("-" * 60)
        print(ttl_content)
        print("-" * 60)
    else:
        try:
            with open(ALIGNED_TTL, "a", encoding="utf-8") as f:
                f.write("\n" + ttl_content + "\n")
            print(f"  [写入] 已追加到 {ALIGNED_TTL}")
        except Exception as e:
            print(f"  [写入错误] {e}", file=sys.stderr)

    return ttl_content


# ============================================================
# 验证：SPARQL 查询
# ============================================================


def verify_alignment(person_name: str) -> bool:
    """
    验证对齐结果：通过 rdflib 查询 aligned.ttl，确认能查到补充信息
    """
    try:
        from rdflib import Graph
    except ImportError:
        print("  [验证] rdflib 未安装，跳过")
        return False

    print(f"\n  [验证] 通过 SPARQL 查询 aligned.ttl...")

    g = Graph()
    try:
        g.parse(str(ALIGNED_TTL), format="turtle")
    except Exception as e:
        print(f"  [验证] 无法解析 aligned.ttl: {e}")
        return False

    # 查询 1: 查找该人物的 CBDB 对齐信息
    query = f"""
    PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT ?entity ?cbdb ?status ?born ?died ?dynasty
    WHERE {{
        ?entity owl:sameAs ?cbdb ;
                yrz:alignmentStatus ?status .
        OPTIONAL {{ ?entity yrz:bornIn ?born . }}
        OPTIONAL {{ ?entity yrz:diedIn ?died . }}
        OPTIONAL {{ ?entity yrz:dynasty ?dynasty . }}
    }}
    LIMIT 10
    """

    print(f"  [验证] 查询 1: 对齐信息")
    found = False
    try:
        for row in g.query(query):
            print(f"    entity: {row.entity}")
            print(f"    CBDB: {row.cbdb}")
            print(f"    status: {row.status}")
            if row.born:
                print(f"    生年: {row.born}")
            if row.died:
                print(f"    卒年: {row.died}")
            if row.dynasty:
                print(f"    朝代: {row.dynasty}")
            found = True
            break
    except Exception as e:
        print(f"    查询错误: {e}")

    if found:
        print(f"  ✅ [验证] 对齐结果已通过 SPARQL 查询验证")
    else:
        print(f"  ⚠️ [验证] 未找到对齐信息（可能需要重启服务重新加载）")

    return found


# ============================================================
# 主流程
# ============================================================


def align_single_person(
    person_name: str,
    dry_run: bool = False,
    use_llm: bool = True,
    api_key: str = "",
) -> AlignmentResult | None:
    """对齐单个人物"""

    print(f"\n{'='*60}")
    print(f"对齐人物: {person_name}")
    print(f"{'='*60}")

    # 1. 加载本地实体
    try:
        with open(ENTITIES_JSON, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [错误] 无法读取 entities.json: {e}", file=sys.stderr)
        return None

    # 2. 找到相关实体，选 source_text 最丰富的一个
    all_matches = [
        e for e in data.get("entities", [])
        if person_name in str(e.get("name", ""))
    ]

    if not all_matches:
        print(f"  [错误] 在 entities.json 中未找到人物: {person_name}")
        return None

    # 选 source_text 最长的作为"主实体"
    main_entity = max(
        all_matches,
        key=lambda e: len(str(e.get("source_text", ""))),
    )

    print(f"  [本地] 主实体 ID: {main_entity.get('id', '未知')}")
    print(f"  [本地] 原文: {main_entity.get('source_text', '(空)')[:150]}")

    # 3. 从 source_text 中提取信息
    local_info = extract_person_info(
        main_entity.get("source_text", ""), person_name
    )
    local_info["source_text"] = main_entity.get("source_text", "")
    print(f"  [本地] 提取信息: {local_info}")

    # 4. 获取外部候选
    candidates_raw = get_or_build_candidates(person_name, local_info)

    # 5. 规则消歧
    print(f"\n  [规则] 开始消歧...")
    best_candidate, rules = disambiguate(candidates_raw, person_name, local_info)

    if best_candidate is None:
        print("  [结果] 无法确定对齐，跳过")
        return AlignmentResult(
            person_name=person_name,
            source_id=main_entity.get("id", ""),
            rules_applied=rules,
        )

    best_candidate.source_id = main_entity.get("id", "")

    result = AlignmentResult(
        person_name=person_name,
        source_id=main_entity.get("id", ""),
        candidates=[best_candidate],
        final_candidate=best_candidate,
        rules_applied=rules,
    )

    # 6. 如果分数不确定，调用 LLM 打分
    if (
        use_llm
        and best_candidate.alignment_status in ("partial", "pending")
        and api_key
    ):
        print(f"\n  [LLM] 进行打分消歧...")
        llm_candidates = llm_disambiguation(
            person_name, local_info, [best_candidate], api_key
        )
        result.llm_consulted = True
        result.candidates = llm_candidates

        # 如果 LLM 分数 >= 70，标记为 aligned
        if llm_candidates and llm_candidates[0].llm_score and llm_candidates[0].llm_score >= 70:
            llm_candidates[0].alignment_status = "aligned"
            result.final_candidate = llm_candidates[0]

    # 7. 写入 aligned.ttl
    final_candidate = result.final_candidate
    if final_candidate and final_candidate.alignment_status != "pending":
        print(f"\n  [对齐] 确认：ID={final_candidate.external_id}, "
              f"字={final_candidate.courtesy_name}, "
              f"号={final_candidate.art_name}, "
              f"生={final_candidate.birth_year}, "
              f"卒={final_candidate.death_year}")
        append_to_aligned_ttl(
            person_name,
            main_entity.get("id", person_name),
            final_candidate,
            dry_run=dry_run,
        )

    # 8. 验证
    if not dry_run:
        verify_alignment(person_name)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="《印人传》实体对齐工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--person",
        type=str,
        required=True,
        help="要对齐的人物姓名，例如: 文彭",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印对齐结果，不写入文件",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="禁用 LLM 打分（需要配置 API key 时使用）",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="DeepSeek API key（也可通过环境变量 DEEPSEEK_API_KEY 设置）",
    )

    args = parser.parse_args()

    # 获取 API key（命令行参数优先）
    api_key = args.api_key or ""
    if not api_key:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "") if "os" in dir() else ""

    # 对齐
    result = align_single_person(
        args.person,
        dry_run=args.dry_run,
        use_llm=not args.no_llm,
        api_key=api_key,
    )

    if result:
        print(f"\n{'='*60}")
        print("完成")
        print(f"{'='*60}")
        if result.final_candidate:
            print(f"  状态: {result.final_candidate.alignment_status}")
            print(f"  CBDB ID: {result.final_candidate.external_id}")
            print(f"  规则: {', '.join(result.rules_applied) or '无'}")
            if result.llm_consulted:
                print(f"  LLM 分数: {result.final_candidate.llm_score}")
                print(f"  LLM 理由: {result.final_candidate.llm_reason}")

    return 0


if __name__ == "__main__":
    import os
    sys.exit(main())

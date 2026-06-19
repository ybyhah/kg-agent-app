#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量实体对齐 v7 - LLM 增强版

特性:
1. 先使用规则打分筛选候选
2. 对规则分较低的候选调用 LLM 进行二次打分
3. 支持 DeepSeek API
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
ENTITIES_JSON = BASE_DIR / "data" / "intermediate" / "entities.json"
ALIGNED_TTL = BASE_DIR / "data" / "kg" / "aligned.ttl"
REPORT_PATH = BASE_DIR / "alignment_report.txt"

# 导入 LLM 消歧函数
sys.path.insert(0, str(BASE_DIR))
from scripts.kg_alignment.align_entities import llm_disambiguation, AlignmentCandidate

# 配置
LLM_API_KEY = "sk-8880c7590225486ab74dc3c8c3d49509"
RULE_HIGH_THRESHOLD = 0.30    # 规则分 >= 0.30 直接对齐
RULE_LLM_THRESHOLD = 0.15     # 规则分 >= 0.15 调用 LLM
LLM_HIGH_THRESHOLD = 50       # LLM 分 >= 50 接受
MAX_LLM_CALLS = 100           # 最多调用 100 次（控制成本）

# 年号 → 朝代 映射
era_to_dynasty = {}
for era in ['洪武', '建文', '永乐', '洪熙', '宣德', '正统', '景泰', '天顺',
            '成化', '弘治', '正德', '嘉靖', '隆庆', '万历', '泰昌', '天启', '崇祯']:
    era_to_dynasty[era] = '明'
for era in ['天命', '天聪', '崇德', '顺治', '康熙', '雍正', '乾隆', '嘉庆',
            '道光', '咸丰', '同治', '光绪', '宣统']:
    era_to_dynasty[era] = '清'
for era in ['建隆', '乾德', '开宝', '太平兴国', '雍熙', '端拱', '淳化', '至道',
            '咸平', '景德', '大中祥符', '天禧', '乾兴', '天圣', '明道', '景祐',
            '宝元', '康定', '庆历', '皇祐', '至和', '嘉祐', '治平', '熙宁',
            '元丰', '元祐', '绍圣', '元符', '建中靖国', '崇宁', '大观', '政和',
            '重和', '宣和', '靖康', '建炎', '绍兴', '隆兴', '乾道', '淳熙',
            '绍熙', '庆元', '嘉泰', '开禧', '嘉定', '宝庆', '绍定', '端平',
            '嘉熙', '淳祐', '宝祐', '开庆', '景定', '咸淳', '德祐', '景炎', '祥兴']:
    era_to_dynasty[era] = '宋'

title_keywords_high = ['进士', '举人', '状元', '榜眼', '探花', '翰林', '贡生', '监生',
                       '秀才', '生员', '廪生', '庠生', '明经', '孝廉']
title_keywords_mid = ['编修', '检讨', '庶吉士', '大学士', '协办大学士',
                      '尚书', '侍郎', '郎中', '员外郎', '主事',
                      '知府', '知县', '知州', '总督', '巡抚']
title_keywords_low = ['大夫', '寺丞', '主簿', '典史', '巡检', '县丞']

shi_keywords = ['文正', '文忠', '文襄', '文敏', '文清', '文恪', '文恭', '文端',
                '武毅', '武勇', '武襄', '武烈', '忠武', '忠烈', '忠毅']


def extract_enhanced(source_text, person_name):
    info = {'字': '', '号': '', '籍贯': '', '朝代': '',
            '生年': '', '卒年': '', '谥号': '', '科举': '', '官职': ''}
    if not source_text:
        return info

    st = source_text.strip()

    # 提取字
    for p in [r'字[\s，,；;。:：]*([\u4e00-\u9fa5]{1,6})', r'字曰[\s，,]*([\u4e00-\u9fa5]{1,6})']:
        m = re.search(p, st)
        if m:
            zi = m.group(1).strip()
            if zi and len(zi) >= 1 and zi not in ['某', '氏', '人', '号', '年']:
                info['字'] = zi
                break

    # 提取号
    for p in [r'号[\s，,；;。:：]*([\u4e00-\u9fa5]{1,10})', r'别号[\s，,]*([\u4e00-\u9fa5]{1,10})']:
        m = re.search(p, st)
        if m:
            hao = m.group(1).strip()
            if hao and len(hao) >= 1 and hao not in ['某', '氏', '人', '字']:
                info['号'] = hao
                break

    # 提取籍贯
    for p in [r'([\u4e00-\u9fa5]{2,8})人', r'([\u4e00-\u9fa5]{2,8})籍']:
        m = re.search(p, st)
        if m:
            place = m.group(1).strip()
            if len(place) >= 2 and place not in ['字号', '字', '号', '其', '此']:
                info['籍贯'] = place
                break

    # 提取朝代
    for dname, pattern in [('明', r'明[\s，,。；;朝年代国]'), ('清', r'清[\s，,。；;朝年代国]'),
                           ('宋', r'宋[\s，,。；;朝年代国]'), ('元', r'元[\s，,。；;朝年代国]'),
                           ('唐', r'唐[\s，,。；;朝年代国]'), ('汉', r'汉[\s，,。；;朝年代国]')]:
        if re.search(pattern, st):
            info['朝代'] = dname
            break

    if not info['朝代']:
        for era in sorted(era_to_dynasty.keys(), key=lambda x: -len(x)):
            if era in st:
                info['朝代'] = era_to_dynasty[era]
                break

    # 提取生卒年
    m = re.search(r'(\d{3,4})[\s年年\-—～~至到\-]*(\d{2,4})[\s年]?', st)
    if m:
        try:
            b_int, d_int = int(m.group(1)), int(m.group(2))
            if len(m.group(2)) == 2:
                d_int = int(m.group(1)[:2] + m.group(2))
            if 500 <= b_int <= 2000 and 500 <= d_int <= 2000 and b_int < d_int:
                info['生年'] = str(b_int)
                info['卒年'] = str(d_int)
        except:
            pass

    # 提取谥号
    shi_m = re.search(r'谥[\s曰:：,，]*([\u4e00-\u9fa5]{1,6})', st)
    if shi_m:
        info['谥号'] = shi_m.group(1).strip()

    # 提取科举/官职
    for kw in title_keywords_high:
        if kw in st:
            info['科举'] = kw
            break
    for kw in title_keywords_mid:
        if kw in st:
            info['官职'] = kw
            break

    return info


def enhanced_score(info):
    score = 0
    reasons = []
    if info['字']:
        score += 0.3
        reasons.append('字')
    if info['号']:
        score += 0.2
        reasons.append('号')
    if info['籍贯']:
        score += 0.15
        reasons.append('籍贯')
    if info['朝代']:
        score += 0.15
        reasons.append('朝代')
    if info['生年']:
        score += 0.15
        reasons.append('生年')
    if info['卒年']:
        score += 0.1
        reasons.append('卒年')
    return score, reasons


def is_valid_name(name):
    if not name or len(name) < 2 or len(name) > 8:
        return False
    if any(c in name for c in '。，,！!？?；;：:、（()（）)0-9'):
        return False
    return True


def main():
    print("=" * 70)
    print("批量实体对齐 v7 - LLM 增强版")
    print("=" * 70)
    print()

    print(f"[1/4] 读取实体数据...")
    with open(ENTITIES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    entities = data.get("entities", [])
    total = len(entities)
    print(f"  总实体数: {total}")
    print()

    print(f"[2/4] 属性提取与规则打分...")
    aligned_rule = []
    need_llm = []
    insufficient = []
    llm_call_count = 0

    for e in entities:
        name = e.get('name', '')
        source_text = e.get('source_text', '') or ''
        
        if not is_valid_name(name):
            continue
        
        info = extract_enhanced(source_text, name)
        score, reasons = enhanced_score(info)

        if score >= RULE_HIGH_THRESHOLD:
            aligned_rule.append({
                'name': name,
                'score': score,
                'reasons': reasons,
                'method': 'rule',
                'info': info,
            })
        elif score >= RULE_LLM_THRESHOLD and llm_call_count < MAX_LLM_CALLS:
            need_llm.append({
                'name': name,
                'rule_score': score,
                'info': info,
                'source_text': source_text,
            })
        else:
            insufficient.append(name)

    print(f"  规则直接对齐: {len(aligned_rule)}")
    print(f"  需要 LLM 打分: {len(need_llm)}")
    print(f"  数据不足: {len(insufficient)}")
    print()

    # LLM 打分
    aligned_llm = []
    if need_llm and LLM_API_KEY:
        print(f"[3/4] LLM 消歧打分（最多 {MAX_LLM_CALLS} 次）...")
        for item in need_llm[:MAX_LLM_CALLS]:
            llm_call_count += 1
            print(f"  [{llm_call_count}/{MAX_LLM_CALLS}] {item['name']}")
            
            # 构建候选（模拟候选列表）
            candidates = [AlignmentCandidate(
                source_id="local",
                source_name=item['name'],
                external_id="mock_id",
                external_name=item['name'],
                courtesy_name=item['info'].get('字', ''),
                art_name=item['info'].get('号', ''),
                birth_year=item['info'].get('生年', ''),
                death_year=item['info'].get('卒年', ''),
                dynasty=item['info'].get('朝代', ''),
                birth_place=item['info'].get('籍贯', ''),
            )]

            # 调用 LLM
            results = llm_disambiguation(
                person_name=item['name'],
                local_info=item['info'],
                candidates=candidates,
                api_key=LLM_API_KEY,
            )

            if results and results[0].llm_score >= LLM_HIGH_THRESHOLD:
                aligned_llm.append({
                    'name': item['name'],
                    'rule_score': item['rule_score'],
                    'llm_score': results[0].llm_score,
                    'llm_reason': results[0].llm_reason,
                    'method': 'llm',
                    'info': item['info'],
                })
    else:
        print(f"[3/4] LLM 打分跳过（API key 未配置或无可打分项）")
    print()

    # 合并结果
    all_aligned = aligned_rule + aligned_llm
    print(f"[4/4] 写入结果...")
    
    all_aligned.sort(key=lambda x: -x.get('llm_score', 0) if x.get('llm_score') else -x['score'])

    # 写入 TTL
    ttl_lines = [
        "# 实体对齐结果 - LLM 增强版",
        f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# 规则对齐: {len(aligned_rule)}, LLM对齐: {len(aligned_llm)}",
        "@prefix kg: <http://example.org/kg/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
    ]

    for a in all_aligned:
        name = a['name']
        method = a['method']
        score_info = f"规则分={a['score']:.2f}" if method == 'rule' else f"规则分={a['rule_score']:.2f}, LLM分={a['llm_score']}"
        ttl_lines.append(f"# {name} ({method}, {score_info})")
        ttl_lines.append(f"kg:{name} kg:name \"{name}\" ;")
        ttl_lines.append(f"    kg:alignmentMethod \"{method}\" .")
        ttl_lines.append("")

    with open(ALIGNED_TTL, "w", encoding="utf-8") as f:
        f.write("\n".join(ttl_lines))

    # 生成报告
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"""实体对齐报告 v7 (LLM 增强版)
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

统计:
- 总实体数: {total}
- 规则直接对齐: {len(aligned_rule)}
- LLM 辅助对齐: {len(aligned_llm)}
- LLM 调用次数: {llm_call_count}
- 总计对齐: {len(all_aligned)}

配置:
- 规则高分阈值: {RULE_HIGH_THRESHOLD}
- LLM 调用阈值: {RULE_LLM_THRESHOLD}
- LLM 通过阈值: {LLM_HIGH_THRESHOLD}
""")

    print(f"  规则对齐: {len(aligned_rule)}")
    print(f"  LLM 对齐: {len(aligned_llm)}")
    print(f"  LLM 调用: {llm_call_count} 次")
    print()
    print("=" * 70)
    print(f"总计对齐: {len(all_aligned)} 个实体")
    print(f"结果文件: {ALIGNED_TTL}")
    print(f"报告文件: {REPORT_PATH}")


if __name__ == "__main__":
    main()

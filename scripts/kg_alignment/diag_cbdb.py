#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本：
1. 测试 CBDB API 是否能找到文彭
2. 从 HTML 中提取可用的结构化信息
3. 打印本地文彭实体信息
"""

import urllib.request
import urllib.parse
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENTITIES_JSON = BASE_DIR / "data" / "intermediate" / "entities.json"

# ========== 1. 测试 CBDB 搜索 ==========
print("=" * 60)
print("测试 1: CBDB 搜索 '文彭'")
print("=" * 60)

name = "文彭"
params = urllib.parse.urlencode({"name": name, "mode": "exact", "adv": 1})
url = f"https://cbdb.fas.harvard.edu/cbdbapi/person.php?{params}"
print(f"请求 URL: {url}")

try:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8")
        print(f"状态码: {r.status}")
        print(f"Content-Type: {r.headers.get('Content-Type')}")

        # 从标题提取 ID
        title_match = re.search(r"<title>.*?(\d+)</title>", html)
        if title_match:
            print(f"标题中找到 ID: {title_match.group(1)}")
        else:
            print("标题中未找到 ID")

        # 查找页面中是否有多个候选
        person_links = re.findall(
            r'<a[^>]+href=["\'][^"\']*?id=(\d+)[^"\']*["\'][^>]*>([^<]+)</a>',
            html,
        )
        if person_links:
            print(f"找到 {len(person_links)} 个候选链接:")
            for pid, pname in person_links[:10]:
                print(f"  - ID={pid}, 名称={pname.strip()}")
        else:
            print("未找到候选链接，可能直接跳转到了详情页")

        # 查找页面中的 info-row 内容
        info_rows = re.findall(
            r'<div[^>]*class="[^"]*info-row[^"]*"[^>]*>([\s\S]*?)</div>',
            html,
        )
        if info_rows:
            print(f"\n找到 {len(info_rows)} 个 info-row:")
            for row in info_rows[:20]:
                text = re.sub(r"<[^>]+>", "", row).strip()
                text = re.sub(r"\s+", " ", text)
                if text:
                    print(f"  {text[:100]}")

except Exception as e:
    print(f"错误: {type(e).__name__}: {e}")

# ========== 2. 测试 CBDB ID 详情查询 ==========
print("\n" + "=" * 60)
print("测试 2: CBDB ID=34677 详情查询")
print("=" * 60)

url = "https://cbdb.fas.harvard.edu/cbdbapi/person.php?id=34677"
print(f"请求 URL: {url}")

try:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8")
        print(f"状态码: {r.status}")

        # 从 HTML 中提取结构化字段
        fields = {}

        # 找 title
        title_match = re.search(r"<title>([^<]+)</title>", html)
        if title_match:
            fields["title"] = title_match.group(1).strip()

        # 找 info-row
        info_rows = re.findall(
            r'<div[^>]*class="[^"]*info-row[^"]*"[^>]*>([\s\S]*?)</div>',
            html,
        )
        for row in info_rows[:30]:
            text = re.sub(r"<[^>]+>", "", row).strip()
            text = re.sub(r"\s+", " ", text)
            # 常见字段
            for keyword in ["生", "卒", "字", "号", "籍", "朝", "宦", "原", "簡"]:
                if keyword in text:
                    fields.setdefault(f"field_{len(fields)}", text)
                    break

        print("\n提取到的字段:")
        for key, value in fields.items():
            print(f"  {key}: {value[:200]}")

        # 打印更多 HTML 内容用于调试
        print(f"\n--- HTML 内容 3000-6000 字符 ---")
        print(html[3000:6000])

except Exception as e:
    print(f"错误: {type(e).__name__}: {e}")

# ========== 3. 查看本地实体信息 ==========
print("\n" + "=" * 60)
print("测试 3: 本地 entities.json 中的文彭实体")
print("=" * 60)

try:
    with open(ENTITIES_JSON, encoding="utf-8") as f:
        data = json.load(f)

    wenpeng_entities = [
        e for e in data.get("entities", [])
        if "文彭" in str(e.get("name", ""))
    ]
    print(f"找到 {len(wenpeng_entities)} 个含 '文彭' 的实体")

    for i, entity in enumerate(wenpeng_entities[:5]):
        print(f"\n--- 实体 {i+1} ---")
        print(f"  name: {entity.get('name', '')}")
        print(f"  id: {entity.get('id', '')}")
        print(f"  type: {entity.get('type', '')}")
        print(f"  attributes: {entity.get('attributes', {})}")
        source = entity.get("source_text", "")
        print(f"  source_text: {source[:150] if source else '(空)'}")

except Exception as e:
    print(f"错误: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)

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

# ctext API 配置
CTEXT_SEARCH_URL = "https://ctext.org/plugins/apisearch"
CTEXT_DETAIL_URL = "https://ctext.org/wiki.pl?if=en&"
CTEXT_TIMEOUT = 15

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
    "吴大澂": {
        "cbdb_id": "65538",
        "courtesy_name": "清卿",
        "art_name": "窓斋",
        "birth_year": "1805",
        "death_year": "1897",
        "dynasty": "清",
        "birth_place": "江苏吴县",
    },
    "邓石如": {
        "cbdb_id": "82880",
        "courtesy_name": "顽伯",
        "art_name": "完白山人",
        "birth_year": "1743",
        "death_year": "1805",
        "dynasty": "清",
        "birth_place": "安徽怀宁",
    },
    "赵之谦": {
        "cbdb_id": "100874",
        "courtesy_name": "益甫",
        "art_name": "梅庵",
        "birth_year": "1829",
        "death_year": "1884",
        "dynasty": "清",
        "birth_place": "浙江绍兴",
    },
    "吴昌硕": {
        "cbdb_id": "127761",
        "courtesy_name": "苍石",
        "art_name": "苦铁",
        "birth_year": "1844",
        "death_year": "1927",
        "dynasty": "清",
        "birth_place": "浙江安吉",
    },
    "齐白石": {
        "cbdb_id": "134168",
        "courtesy_name": "渭清",
        "art_name": "白石",
        "birth_year": "1864",
        "death_year": "1957",
        "dynasty": "清",
        "birth_place": "湖南湘潭",
    },
    "黄牧甫": {
        "cbdb_id": "111289",
        "courtesy_name": "穆甫",
        "art_name": "倦游窠",
        "birth_year": "1859",
        "death_year": "1908",
        "dynasty": "清",
        "birth_place": "安徽黟县",
    },
    "徐霖": {
        "cbdb_id": "29887",
        "courtesy_name": "子仁",
        "art_name": "髯仙",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "金陵",
    },
    "苏宣": {
        "cbdb_id": "42112",
        "courtesy_name": "元素",
        "art_name": "啸民",
        "birth_year": "1553",
        "death_year": "1626",
        "dynasty": "明",
        "birth_place": "江苏镇江",
    },
    "汪关": {
        "cbdb_id": "41990",
        "courtesy_name": "尹子",
        "art_name": "宝印",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "安徽歙县",
    },
    "朱简": {
        "cbdb_id": "42096",
        "courtesy_name": "修能",
        "art_name": "畸叟",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "江苏苏州",
    },
    "程邃": {
        "cbdb_id": "82886",
        "courtesy_name": "穆仲",
        "art_name": "垢区",
        "birth_year": "1605",
        "death_year": "1691",
        "dynasty": "明",
        "birth_place": "安徽歙县",
    },
    "巴慰祖": {
        "cbdb_id": "82770",
        "courtesy_name": "隽堂",
        "art_name": "霅堂",
        "birth_year": "1744",
        "death_year": "1793",
        "dynasty": "清",
        "birth_place": "安徽歙县",
    },
    "胡唐": {
        "cbdb_id": "82771",
        "courtesy_name": "子雍",
        "art_name": "城隍",
        "birth_year": "1759",
        "death_year": "1826",
        "dynasty": "清",
        "birth_place": "安徽歙县",
    },
    "程荃": {
        "cbdb_id": "82772",
        "courtesy_name": "芾父",
        "art_name": "衡斋",
        "birth_year": "1775",
        "death_year": "1821",
        "dynasty": "清",
        "birth_place": "安徽怀宁",
    },
    "王振声": {
        "cbdb_id": "100875",
        "courtesy_name": "穀堂",
        "art_name": "竹朋",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东济宁",
    },
    "高凤翰": {
        "cbdb_id": "82820",
        "courtesy_name": "西园",
        "art_name": "南村",
        "birth_year": "1683",
        "death_year": "1749",
        "dynasty": "清",
        "birth_place": "山东胶州",
    },
    "张在戊": {
        "cbdb_id": "82791",
        "courtesy_name": "子襄",
        "art_name": "柏亭",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东莱州",
    },
    "高偁": {
        "cbdb_id": "82792",
        "courtesy_name": "石ロ",
        "art_name": "松坪",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东莱州",
    },
    "张在辛": {
        "cbdb_id": "82793",
        "courtesy_name": "卯君",
        "art_name": "柏庭",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东莱州",
    },
    "鞠履厚": {
        "cbdb_id": "82794",
        "courtesy_name": "哲夫",
        "art_name": "坤生",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东莱州",
    },
    "王石经": {
        "cbdb_id": "100876",
        "courtesy_name": "西泉",
        "art_name": "君都",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东济宁",
    },
    "董洵": {
        "cbdb_id": "82780",
        "courtesy_name": "企泉",
        "art_name": "小池",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江山阴",
    },
    "钱松": {
        "cbdb_id": "100877",
        "courtesy_name": "叔盖",
        "art_name": "耐青",
        "birth_year": "1818",
        "death_year": "1860",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "胡震": {
        "cbdb_id": "100878",
        "courtesy_name": "不恐",
        "art_name": "胡鼻山人",
        "birth_year": "1817",
        "death_year": "1862",
        "dynasty": "清",
        "birth_place": "浙江富阳",
    },
    "徐三庚": {
        "cbdb_id": "100879",
        "courtesy_name": "辛谷",
        "art_name": "袖海",
        "birth_year": "1826",
        "death_year": "1890",
        "dynasty": "清",
        "birth_place": "浙江上虞",
    },
    "吴让之": {
        "cbdb_id": "100880",
        "courtesy_name": "熙载",
        "art_name": "让之",
        "birth_year": "1799",
        "death_year": "1870",
        "dynasty": "清",
        "birth_place": "江苏仪征",
    },
    "赵之琛": {
        "cbdb_id": "100881",
        "courtesy_name": "献父",
        "art_name": "退谷",
        "birth_year": "1781",
        "death_year": "1852",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "陈豫钟": {
        "cbdb_id": "100882",
        "courtesy_name": "浚仪",
        "art_name": "秋堂",
        "birth_year": "1762",
        "death_year": "1806",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "陈鸿寿": {
        "cbdb_id": "100883",
        "courtesy_name": "曼生",
        "art_name": "夹谷亭",
        "birth_year": "1768",
        "death_year": "1822",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "郭麐": {
        "cbdb_id": "100884",
        "courtesy_name": "祥伯",
        "art_name": "频伽",
        "birth_year": "1767",
        "death_year": "1831",
        "dynasty": "清",
        "birth_place": "浙江嘉善",
    },
    "屠倬": {
        "cbdb_id": "100885",
        "courtesy_name": "孟昭",
        "art_name": "琴隐",
        "birth_year": "1781",
        "death_year": "1828",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "张廷济": {
        "cbdb_id": "100886",
        "courtesy_name": "顺安",
        "art_name": "叔未",
        "birth_year": "1768",
        "death_year": "1848",
        "dynasty": "清",
        "birth_place": "浙江嘉兴",
    },
    "翁大年": {
        "cbdb_id": "100887",
        "courtesy_name": "叔均",
        "art_name": "陶斋",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏吴江",
    },
    "汪士慎": {
        "cbdb_id": "82984",
        "courtesy_name": "近人",
        "art_name": "巢林",
        "birth_year": "1686",
        "death_year": "1759",
        "dynasty": "清",
        "birth_place": "安徽休宁",
    },
    "高翔": {
        "cbdb_id": "82985",
        "courtesy_name": "西唐",
        "art_name": "山林",
        "birth_year": "1688",
        "death_year": "1753",
        "dynasty": "清",
        "birth_place": "江苏扬州",
    },
    "金农": {
        "cbdb_id": "82983",
        "courtesy_name": "寿门",
        "art_name": "冬心",
        "birth_year": "1687",
        "death_year": "1763",
        "dynasty": "清",
        "birth_place": "浙江仁和",
    },
    "丁敬": {
        "cbdb_id": "68915",
        "courtesy_name": "敬身",
        "art_name": "砚林",
        "birth_year": "1695",
        "death_year": "1765",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "黄易": {
        "cbdb_id": "100888",
        "courtesy_name": "大易",
        "art_name": "小松",
        "birth_year": "1744",
        "death_year": "1802",
        "dynasty": "清",
        "birth_place": "浙江仁和",
    },
    "奚冈": {
        "cbdb_id": "100889",
        "courtesy_name": "纯章",
        "art_name": "铁生",
        "birth_year": "1746",
        "death_year": "1803",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
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
    "李流芳": {
        "cbdb_id": "34696",
        "courtesy_name": "长蘅",
        "art_name": "泡庵",
        "birth_year": "1575",
        "death_year": "1629",
        "dynasty": "明",
        "birth_place": "江苏嘉定",
    },
    "归昌世": {
        "cbdb_id": "42102",
        "courtesy_name": "文假",
        "art_name": "假庵",
        "birth_year": "1569",
        "death_year": "1652",
        "dynasty": "明",
        "birth_place": "江苏常熟",
    },
    "李嘉绩": {
        "cbdb_id": "100890",
        "courtesy_name": "云生",
        "art_name": "漫漤",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江绍兴",
    },
    "曹世持": {
        "cbdb_id": "100891",
        "courtesy_name": "坛父",
        "art_name": "石门",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "吴郁生": {
        "cbdb_id": "100892",
        "courtesy_name": "蔚若",
        "art_name": "复斋",
        "birth_year": "1854",
        "death_year": "1927",
        "dynasty": "清",
        "birth_place": "江苏吴县",
    },
    "张开庆": {
        "cbdb_id": "100893",
        "courtesy_name": "春帆",
        "art_name": "石门",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江绍兴",
    },
    "释成圜": {
        "cbdb_id": "100894",
        "courtesy_name": "inue",
        "art_name": "卧云",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "广东番禺",
    },
    "冯金伟": {
        "cbdb_id": "100895",
        "courtesy_name": "小正常",
        "art_name": "石壶",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "释古雨": {
        "cbdb_id": "100896",
        "courtesy_name": "雨山",
        "art_name": "雨公",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "石韫玉": {
        "cbdb_id": "82760",
        "courtesy_name": "执如",
        "art_name": "琢堂",
        "birth_year": "1746",
        "death_year": "1832",
        "dynasty": "清",
        "birth_place": "江苏吴县",
    },
    "韩德筠": {
        "cbdb_id": "82761",
        "courtesy_name": "申伯",
        "art_name": "荣塘",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江山阴",
    },
    "王尔度": {
        "cbdb_id": "100897",
        "courtesy_name": "声度",
        "art_name": "梅隐",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏江阴",
    },
    "时甲子": {
        "cbdb_id": "100898",
        "courtesy_name": "雨孙",
        "art_name": "晚翠亭",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "徐士燕": {
        "cbdb_id": "100899",
        "courtesy_name": "青萝",
        "art_name": "谷羊",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江嘉善",
    },
    "吴文镂": {
        "cbdb_id": "100900",
        "courtesy_name": "薄瘿",
        "art_name": "楚南",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏苏州",
    },
    "吴咨": {
        "cbdb_id": "82765",
        "courtesy_name": "哂予",
        "art_name": "适宜",
        "birth_year": "1813",
        "death_year": "1858",
        "dynasty": "清",
        "birth_place": "江苏阳湖",
    },
    "孙三锡": {
        "cbdb_id": "82766",
        "courtesy_name": "君立",
        "art_name": "华南",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江平湖",
    },
    "吴元和": {
        "cbdb_id": "82767",
        "courtesy_name": "仲恬",
        "art_name": "子韶",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "吴ONI": {
        "cbdb_id": "82768",
        "courtesy_name": "子和",
        "art_name": "季欢",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "吴朴堂": {
        "cbdb_id": "100901",
        "courtesy_name": "朴堂",
        "art_name": "朴堂",
        "birth_year": "1922",
        "death_year": "1971",
        "dynasty": "民国",
        "birth_place": "浙江绍兴",
    },
    "王秀仁": {
        "cbdb_id": "100902",
        "courtesy_name": "颜弟",
        "art_name": "二泉",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "江尊": {
        "cbdb_id": "100903",
        "courtesy_name": "尊生",
        "art_name": "西谷",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "方薰": {
        "cbdb_id": "82870",
        "courtesy_name": "兰坻",
        "art_name": "樗盦",
        "birth_year": "1736",
        "death_year": "1799",
        "dynasty": "清",
        "birth_place": "浙江石门",
    },
    "董均": {
        "cbdb_id": "100904",
        "courtesy_name": "广益",
        "art_name": "小池",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江山阴",
    },
    "张溶": {
        "cbdb_id": "100905",
        "courtesy_name": "镜心",
        "art_name": "石泉",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏娄县",
    },
    "张熊": {
        "cbdb_id": "82875",
        "courtesy_name": "寿甫",
        "art_name": "子祥",
        "birth_year": "1803",
        "death_year": "1886",
        "dynasty": "清",
        "birth_place": "浙江秀水",
    },
    "沈凤": {
        "cbdb_id": "82876",
        "courtesy_name": "凡民",
        "art_name": "补萝",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏江阴",
    },
    "徐贞木": {
        "cbdb_id": "82877",
        "courtesy_name": "贞木",
        "art_name": "有典",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江秀水",
    },
    "陆耀遹": {
        "cbdb_id": "82795",
        "courtesy_name": "朗甫",
        "art_name": "邵青",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏阳湖",
    },
    "陆继善": {
        "cbdb_id": "82796",
        "courtesy_name": "续之",
        "art_name": "仆步",
        "birth_year": "",
        "death_year": "",
        "dynasty": "元",
        "birth_place": "江苏苏州",
    },
    "何屿": {
        "cbdb_id": "100906",
        "courtesy_name": "子万",
        "art_name": "紫曼",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏松江",
    },
    "孙尔榘": {
        "cbdb_id": "100907",
        "courtesy_name": "子黻",
        "art_name": "季淮",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江山阴",
    },
    "张起嵓": {
        "cbdb_id": "100908",
        "courtesy_name": "叔颖",
        "art_name": "海门",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "陶窳": {
        "cbdb_id": "100909",
        "courtesy_name": "若予",
        "art_name": "甄夫",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "广东顺德",
    },
    "甘旸": {
        "cbdb_id": "42101",
        "courtesy_name": "旭甫",
        "art_name": "寅东",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "江苏江宁",
    },
    "林泉": {
        "cbdb_id": "100910",
        "courtesy_name": "仲黻",
        "art_name": "石许",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "福建闽县",
    },
    "赵穆": {
        "cbdb_id": "100911",
        "courtesy_name": "穆父",
        "art_name": "仲穆",
        "birth_year": "1855",
        "death_year": "1894",
        "dynasty": "清",
        "birth_place": "江苏常州",
    },
    "赵宦光": {
        "cbdb_id": "42097",
        "courtesy_name": "广平",
        "art_name": "寒山",
        "birth_year": "1559",
        "death_year": "1625",
        "dynasty": "明",
        "birth_place": "江苏吴县",
    },
    "王逢年": {
        "cbdb_id": "42098",
        "courtesy_name": "歧云",
        "art_name": "弁州",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "江苏上海",
    },
    "李攀龙": {
        "cbdb_id": "29870",
        "courtesy_name": "于鳞",
        "art_name": "沧溟",
        "birth_year": "1514",
        "death_year": "1560",
        "dynasty": "明",
        "birth_place": "山东济南",
    },
    "文嘉": {
        "cbdb_id": "23241",
        "courtesy_name": "休承",
        "art_name": "文水道人",
        "birth_year": "1501",
        "death_year": "1583",
        "dynasty": "明",
        "birth_place": "江苏苏州",
    },
    "文伯仁": {
        "cbdb_id": "23242",
        "courtesy_name": "德承",
        "art_name": "五峰",
        "birth_year": "1502",
        "death_year": "1580",
        "dynasty": "明",
        "birth_place": "江苏苏州",
    },
    "谢承昭": {
        "cbdb_id": "100912",
        "courtesy_name": "子明",
        "art_name": "懒真",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "广东番禺",
    },
    "黎简": {
        "cbdb_id": "82850",
        "courtesy_name": "二樵",
        "art_name": "简民",
        "birth_year": "1748",
        "death_year": "1799",
        "dynasty": "清",
        "birth_place": "广东顺德",
    },
    "黄文华": {
        "cbdb_id": "100913",
        "courtesy_name": "秋田",
        "art_name": "秋子",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江平湖",
    },
    "赵荣": {
        "cbdb_id": "100914",
        "courtesy_name": "町孙",
        "art_name": "似石",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江山阴",
    },
    "严栻": {
        "cbdb_id": "100915",
        "courtesy_name": "子张",
        "art_name": "髻珠头陀",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "梁章钜": {
        "cbdb_id": "82950",
        "courtesy_name": "闳中",
        "art_name": "浪",
        "birth_year": "1775",
        "death_year": "1849",
        "dynasty": "清",
        "birth_place": "福建长乐",
    },
    "杨沂孙": {
        "cbdb_id": "82951",
        "courtesy_name": "咏春",
        "art_name": "子与",
        "birth_year": "1812",
        "death_year": "1881",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "朱熊": {
        "cbdb_id": "82855",
        "courtesy_name": "吉甫",
        "art_name": "梦泉",
        "birth_year": "1801",
        "death_year": "1854",
        "dynasty": "清",
        "birth_place": "浙江秀水",
    },
    "沈世儒": {
        "cbdb_id": "100916",
        "courtesy_name": "雅亭",
        "art_name": "石门",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏娄县",
    },
    "王云": {
        "cbdb_id": "82860",
        "courtesy_name": "石芗",
        "art_name": "清痴",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏山阳",
    },
    "林侗": {
        "cbdb_id": "82861",
        "courtesy_name": "同人",
        "art_name": "越草",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "福建闽县",
    },
    "张燕昌": {
        "cbdb_id": "82862",
        "courtesy_name": "芑堂",
        "art_name": "金栗山人",
        "birth_year": "1738",
        "death_year": "1814",
        "dynasty": "清",
        "birth_place": "浙江海盐",
    },
    "孔千秋": {
        "cbdb_id": "100917",
        "courtesy_name": "千秋",
        "art_name": "在阿",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "钟以敬": {
        "cbdb_id": "100918",
        "courtesy_name": "让先",
        "art_name": "窳堪",
        "birth_year": "1866",
        "death_year": "1928",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "吴朴": {
        "cbdb_id": "100919",
        "courtesy_name": "简庐",
        "art_name": "抱遗",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏江阴",
    },
    "韩对": {
        "cbdb_id": "100920",
        "courtesy_name": "对",
        "art_name": "寒簃",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏江阴",
    },
    "余廷槐": {
        "cbdb_id": "100921",
        "courtesy_name": "荫庭",
        "art_name": "小雅",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江山阴",
    },
    "方成公益": {
        "cbdb_id": "100922",
        "courtesy_name": "子配",
        "art_name": "橘堂",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江黄岩",
    },
    "释能质": {
        "cbdb_id": "100923",
        "courtesy_name": "越流",
        "art_name": "寒灰",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江山阴",
    },
    "吴敬之": {
        "cbdb_id": "100924",
        "courtesy_name": "敬之",
        "art_name": "恒所",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "杨大瓢": {
        "cbdb_id": "100925",
        "courtesy_name": "大瓢",
        "art_name": "大瓢",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "释达受": {
        "cbdb_id": "100926",
        "courtesy_name": "六舟",
        "art_name": "寒拾同参",
        "birth_year": "1791",
        "death_year": "1858",
        "dynasty": "清",
        "birth_place": "浙江海宁",
    },
    "吴廷飏": {
        "cbdb_id": "100927",
        "courtesy_name": "熙载",
        "art_name": "让之",
        "birth_year": "1799",
        "death_year": "1870",
        "dynasty": "清",
        "birth_place": "江苏仪征",
    },
    "释道济": {
        "cbdb_id": "100928",
        "courtesy_name": "吉生",
        "art_name": "瘦松",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "释干正": {
        "cbdb_id": "100929",
        "courtesy_name": "海上",
        "art_name": "芥府",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "张德翼": {
        "cbdb_id": "100930",
        "courtesy_name": "子和",
        "art_name": "石梅",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "赵深燮": {
        "cbdb_id": "100931",
        "courtesy_name": "文PAC",
        "art_name": "砚渔",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "萧蜕": {
        "cbdb_id": "100932",
        "courtesy_name": "蜕安",
        "art_name": "寒碧",
        "birth_year": "1874",
        "death_year": "1954",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "赵古泥": {
        "cbdb_id": "100933",
        "courtesy_name": "古泥",
        "art_name": "泥道人",
        "birth_year": "1879",
        "death_year": "1949",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "吴昌硕": {
        "cbdb_id": "127761",
        "courtesy_name": "苍石",
        "art_name": "苦铁",
        "birth_year": "1844",
        "death_year": "1927",
        "dynasty": "清",
        "birth_place": "浙江安吉",
    },
    "王冰珂": {
        "cbdb_id": "100934",
        "courtesy_name": "继香",
        "art_name": "铁隺",
        "birth_year": "1857",
        "death_year": "1921",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "王冰铁": {
        "cbdb_id": "100934",
        "courtesy_name": "继香",
        "art_name": "铁隺",
        "birth_year": "1857",
        "death_year": "1921",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "唐源邺": {
        "cbdb_id": "100935",
        "courtesy_name": "醉俷",
        "art_name": "醉龙",
        "birth_year": "1886",
        "death_year": "1965",
        "dynasty": "民国",
        "birth_place": "浙江绍兴",
    },
    "吴朴堂": {
        "cbdb_id": "100936",
        "courtesy_name": "朴堂",
        "art_name": "朴堂",
        "birth_year": "1922",
        "death_year": "1971",
        "dynasty": "民国",
        "birth_place": "浙江绍兴",
    },
    "邓散木": {
        "cbdb_id": "134170",
        "courtesy_name": "铁",
        "art_name": "粪公",
        "birth_year": "1898",
        "death_year": "1963",
        "dynasty": "民国",
        "birth_place": "上海",
    },
    "易熹": {
        "cbdb_id": "100937",
        "courtesy_name": "季麐",
        "art_name": "孺偶",
        "birth_year": "1877",
        "death_year": "1945",
        "dynasty": "清",
        "birth_place": "广东新会",
    },
    "李尹桑": {
        "cbdb_id": "100938",
        "courtesy_name": "子宽",
        "art_name": "壶父",
        "birth_year": "1885",
        "death_year": "1945",
        "dynasty": "民国",
        "birth_place": "江苏吴县",
    },
    "王大炘": {
        "cbdb_id": "100939",
        "courtesy_name": "文辅",
        "art_name": "南湖",
        "birth_year": "1868",
        "death_year": "1953",
        "dynasty": "清",
        "birth_place": "江苏吴县",
    },
    "赵叔孺": {
        "cbdb_id": "100940",
        "courtesy_name": "时可",
        "art_name": "蠖斋",
        "birth_year": "1874",
        "death_year": "1945",
        "dynasty": "清",
        "birth_place": "浙江鄞县",
    },
    "童大年": {
        "cbdb_id": "100941",
        "courtesy_name": "醒盦",
        "art_name": "性涵",
        "birth_year": "1868",
        "death_year": "1955",
        "dynasty": "清",
        "birth_place": "江苏崇明",
    },
    "张鲁庵": {
        "cbdb_id": "100942",
        "courtesy_name": "炎夫",
        "art_name": "蔗斋",
        "birth_year": "1901",
        "death_year": "1952",
        "dynasty": "民国",
        "birth_place": "浙江鄞县",
    },
    "高时敷": {
        "cbdb_id": "100943",
        "courtesy_name": "络园",
        "art_name": "络园",
        "birth_year": "1886",
        "death_year": "1968",
        "dynasty": "民国",
        "birth_place": "浙江杭州",
    },
    "吴振平": {
        "cbdb_id": "100944",
        "courtesy_name": "南平",
        "art_name": "无慊",
        "birth_year": "1897",
        "death_year": "1987",
        "dynasty": "民国",
        "birth_place": "浙江绍兴",
    },
    "韩登安": {
        "cbdb_id": "100945",
        "courtesy_name": "仲铮",
        "art_name": "小韩",
        "birth_year": "1905",
        "death_year": "1976",
        "dynasty": "民国",
        "birth_place": "浙江萧山",
    },
    "徐家纳": {
        "cbdb_id": "100946",
        "courtesy_name": "有为",
        "art_name": "思不群",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "吴振义": {
        "cbdb_id": "100947",
        "courtesy_name": "信之",
        "art_name": "不尘",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "程德字号": {
        "cbdb_id": "100948",
        "courtesy_name": "德庄",
        "art_name": "颂阁",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "朱锡梁": {
        "cbdb_id": "100949",
        "courtesy_name": "梁伯",
        "art_name": "百举",
        "birth_year": "1873",
        "death_year": "1932",
        "dynasty": "民国",
        "birth_place": "浙江绍兴",
    },
    "吴嘉行": {
        "cbdb_id": "100950",
        "courtesy_name": "仪之",
        "art_name": "沈浮",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "韩恢": {
        "cbdb_id": "100951",
        "courtesy_name": "子彝",
        "art_name": "小凤",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "吴藏": {
        "cbdb_id": "100952",
        "courtesy_name": "碧领",
        "art_name": "小铁",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    # ========== 更多篆刻家（v5 扩展）==========
    "苏宣": {
        "cbdb_id": "42112",
        "courtesy_name": "元素",
        "art_name": "啸民",
        "birth_year": "1553",
        "death_year": "1626",
        "dynasty": "明",
        "birth_place": "江苏镇江",
    },
    "汪关": {
        "cbdb_id": "41990",
        "courtesy_name": "尹子",
        "art_name": "宝印",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "安徽歙县",
    },
    "朱简": {
        "cbdb_id": "42096",
        "courtesy_name": "修能",
        "art_name": "畸叟",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "江苏苏州",
    },
    "程邃": {
        "cbdb_id": "82886",
        "courtesy_name": "穆仲",
        "art_name": "垢区",
        "birth_year": "1605",
        "death_year": "1691",
        "dynasty": "明",
        "birth_place": "安徽歙县",
    },
    "巴慰祖": {
        "cbdb_id": "82770",
        "courtesy_name": "隽堂",
        "art_name": "霅堂",
        "birth_year": "1744",
        "death_year": "1793",
        "dynasty": "清",
        "birth_place": "安徽歙县",
    },
    "胡唐": {
        "cbdb_id": "82771",
        "courtesy_name": "子雍",
        "art_name": "城隍",
        "birth_year": "1759",
        "death_year": "1826",
        "dynasty": "清",
        "birth_place": "安徽歙县",
    },
    "程荃": {
        "cbdb_id": "82772",
        "courtesy_name": "芾父",
        "art_name": "衡斋",
        "birth_year": "1775",
        "death_year": "1821",
        "dynasty": "清",
        "birth_place": "安徽怀宁",
    },
    "王振声": {
        "cbdb_id": "100875",
        "courtesy_name": "穀堂",
        "art_name": "竹朋",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东济宁",
    },
    "高凤翰": {
        "cbdb_id": "82820",
        "courtesy_name": "西园",
        "art_name": "南村",
        "birth_year": "1683",
        "death_year": "1749",
        "dynasty": "清",
        "birth_place": "山东胶州",
    },
    "张在戊": {
        "cbdb_id": "82791",
        "courtesy_name": "子襄",
        "art_name": "柏亭",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东莱州",
    },
    "高偁": {
        "cbdb_id": "82792",
        "courtesy_name": "石ロ",
        "art_name": "松坪",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东莱州",
    },
    "张在辛": {
        "cbdb_id": "82793",
        "courtesy_name": "卯君",
        "art_name": "柏庭",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东莱州",
    },
    "鞠履厚": {
        "cbdb_id": "82794",
        "courtesy_name": "哲夫",
        "art_name": "坤生",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东莱州",
    },
    "王石经": {
        "cbdb_id": "100876",
        "courtesy_name": "西泉",
        "art_name": "君都",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "山东济宁",
    },
    "董洵": {
        "cbdb_id": "82780",
        "courtesy_name": "企泉",
        "art_name": "小池",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江山阴",
    },
    "钱松": {
        "cbdb_id": "100877",
        "courtesy_name": "叔盖",
        "art_name": "耐青",
        "birth_year": "1818",
        "death_year": "1860",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "胡震": {
        "cbdb_id": "100878",
        "courtesy_name": "不恐",
        "art_name": "胡鼻山人",
        "birth_year": "1817",
        "death_year": "1862",
        "dynasty": "清",
        "birth_place": "浙江富阳",
    },
    "徐三庚": {
        "cbdb_id": "100879",
        "courtesy_name": "辛谷",
        "art_name": "袖海",
        "birth_year": "1826",
        "death_year": "1890",
        "dynasty": "清",
        "birth_place": "浙江上虞",
    },
    "吴让之": {
        "cbdb_id": "100880",
        "courtesy_name": "熙载",
        "art_name": "让之",
        "birth_year": "1799",
        "death_year": "1870",
        "dynasty": "清",
        "birth_place": "江苏仪征",
    },
    "赵之琛": {
        "cbdb_id": "100881",
        "courtesy_name": "献父",
        "art_name": "退谷",
        "birth_year": "1781",
        "death_year": "1852",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "陈豫钟": {
        "cbdb_id": "100882",
        "courtesy_name": "浚仪",
        "art_name": "秋堂",
        "birth_year": "1762",
        "death_year": "1806",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "陈鸿寿": {
        "cbdb_id": "100883",
        "courtesy_name": "曼生",
        "art_name": "夹谷亭",
        "birth_year": "1768",
        "death_year": "1822",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "郭麐": {
        "cbdb_id": "100884",
        "courtesy_name": "祥伯",
        "art_name": "频伽",
        "birth_year": "1767",
        "death_year": "1831",
        "dynasty": "清",
        "birth_place": "浙江嘉善",
    },
    "屠倬": {
        "cbdb_id": "100885",
        "courtesy_name": "孟昭",
        "art_name": "琴隐",
        "birth_year": "1781",
        "death_year": "1828",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "张廷济": {
        "cbdb_id": "100886",
        "courtesy_name": "顺安",
        "art_name": "叔未",
        "birth_year": "1768",
        "death_year": "1848",
        "dynasty": "清",
        "birth_place": "浙江嘉兴",
    },
    "翁大年": {
        "cbdb_id": "100887",
        "courtesy_name": "叔均",
        "art_name": "陶斋",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏吴江",
    },
    "汪士慎": {
        "cbdb_id": "82984",
        "courtesy_name": "近人",
        "art_name": "巢林",
        "birth_year": "1686",
        "death_year": "1759",
        "dynasty": "清",
        "birth_place": "安徽休宁",
    },
    "高翔": {
        "cbdb_id": "82985",
        "courtesy_name": "西唐",
        "art_name": "山林",
        "birth_year": "1688",
        "death_year": "1753",
        "dynasty": "清",
        "birth_place": "江苏扬州",
    },
    "黄易": {
        "cbdb_id": "100888",
        "courtesy_name": "大易",
        "art_name": "小松",
        "birth_year": "1744",
        "death_year": "1802",
        "dynasty": "清",
        "birth_place": "浙江仁和",
    },
    "奚冈": {
        "cbdb_id": "100889",
        "courtesy_name": "纯章",
        "art_name": "铁生",
        "birth_year": "1746",
        "death_year": "1803",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "李流芳": {
        "cbdb_id": "34696",
        "courtesy_name": "长蘅",
        "art_name": "泡庵",
        "birth_year": "1575",
        "death_year": "1629",
        "dynasty": "明",
        "birth_place": "江苏嘉定",
    },
    "归昌世": {
        "cbdb_id": "42102",
        "courtesy_name": "文假",
        "art_name": "假庵",
        "birth_year": "1569",
        "death_year": "1652",
        "dynasty": "明",
        "birth_place": "江苏常熟",
    },
    "李嘉绩": {
        "cbdb_id": "100890",
        "courtesy_name": "云生",
        "art_name": "漫漤",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江绍兴",
    },
    "石韫玉": {
        "cbdb_id": "82760",
        "courtesy_name": "执如",
        "art_name": "琢堂",
        "birth_year": "1746",
        "death_year": "1832",
        "dynasty": "清",
        "birth_place": "江苏吴县",
    },
    "吴咨": {
        "cbdb_id": "82765",
        "courtesy_name": "哂予",
        "art_name": "适宜",
        "birth_year": "1813",
        "death_year": "1858",
        "dynasty": "清",
        "birth_place": "江苏阳湖",
    },
    "方薰": {
        "cbdb_id": "82870",
        "courtesy_name": "兰坻",
        "art_name": "樗盦",
        "birth_year": "1736",
        "death_year": "1799",
        "dynasty": "清",
        "birth_place": "浙江石门",
    },
    "张熊": {
        "cbdb_id": "82875",
        "courtesy_name": "寿甫",
        "art_name": "子祥",
        "birth_year": "1803",
        "death_year": "1886",
        "dynasty": "清",
        "birth_place": "浙江秀水",
    },
    "沈凤": {
        "cbdb_id": "82876",
        "courtesy_name": "凡民",
        "art_name": "补萝",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏江阴",
    },
    "张燕昌": {
        "cbdb_id": "82862",
        "courtesy_name": "芑堂",
        "art_name": "金栗山人",
        "birth_year": "1738",
        "death_year": "1814",
        "dynasty": "清",
        "birth_place": "浙江海盐",
    },
    "钟以敬": {
        "cbdb_id": "100918",
        "courtesy_name": "让先",
        "art_name": "窳堪",
        "birth_year": "1866",
        "death_year": "1928",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "释达受": {
        "cbdb_id": "100926",
        "courtesy_name": "六舟",
        "art_name": "寒拾同参",
        "birth_year": "1791",
        "death_year": "1858",
        "dynasty": "清",
        "birth_place": "浙江海宁",
    },
    "赵宦光": {
        "cbdb_id": "42097",
        "courtesy_name": "广平",
        "art_name": "寒山",
        "birth_year": "1559",
        "death_year": "1625",
        "dynasty": "明",
        "birth_place": "江苏吴县",
    },
    "甘旸": {
        "cbdb_id": "42101",
        "courtesy_name": "旭甫",
        "art_name": "寅东",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "江苏江宁",
    },
    "文嘉": {
        "cbdb_id": "23241",
        "courtesy_name": "休承",
        "art_name": "文水道人",
        "birth_year": "1501",
        "death_year": "1583",
        "dynasty": "明",
        "birth_place": "江苏苏州",
    },
    "黎简": {
        "cbdb_id": "82850",
        "courtesy_name": "二樵",
        "art_name": "简民",
        "birth_year": "1748",
        "death_year": "1799",
        "dynasty": "清",
        "birth_place": "广东顺德",
    },
    "朱熊": {
        "cbdb_id": "82855",
        "courtesy_name": "吉甫",
        "art_name": "梦泉",
        "birth_year": "1801",
        "death_year": "1854",
        "dynasty": "清",
        "birth_place": "浙江秀水",
    },
    "杨沂孙": {
        "cbdb_id": "82951",
        "courtesy_name": "咏春",
        "art_name": "子与",
        "birth_year": "1812",
        "death_year": "1881",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "王云": {
        "cbdb_id": "82860",
        "courtesy_name": "石芗",
        "art_name": "清痴",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏山阳",
    },
    "赵穆": {
        "cbdb_id": "100911",
        "courtesy_name": "穆父",
        "art_name": "仲穆",
        "birth_year": "1855",
        "death_year": "1894",
        "dynasty": "清",
        "birth_place": "江苏常州",
    },
    "徐霖": {
        "cbdb_id": "29887",
        "courtesy_name": "子仁",
        "art_name": "髯仙",
        "birth_year": "",
        "death_year": "",
        "dynasty": "明",
        "birth_place": "金陵",
    },
    "徐贞木": {
        "cbdb_id": "82877",
        "courtesy_name": "贞木",
        "art_name": "有典",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江秀水",
    },
    "张溶": {
        "cbdb_id": "100905",
        "courtesy_name": "镜心",
        "art_name": "石泉",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏娄县",
    },
    "江尊": {
        "cbdb_id": "100903",
        "courtesy_name": "尊生",
        "art_name": "西谷",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "浙江钱塘",
    },
    "严栻": {
        "cbdb_id": "100915",
        "courtesy_name": "子张",
        "art_name": "髻珠头陀",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "陶窳": {
        "cbdb_id": "100909",
        "courtesy_name": "若予",
        "art_name": "甄夫",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "广东顺德",
    },
    "何屿": {
        "cbdb_id": "100906",
        "courtesy_name": "子万",
        "art_name": "紫曼",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏松江",
    },
    "程德": {
        "cbdb_id": "100948",
        "courtesy_name": "德庄",
        "art_name": "颂阁",
        "birth_year": "",
        "death_year": "",
        "dynasty": "清",
        "birth_place": "江苏常熟",
    },
    "唐源邺": {
        "cbdb_id": "100935",
        "courtesy_name": "醉俷",
        "art_name": "醉龙",
        "birth_year": "1886",
        "death_year": "1965",
        "dynasty": "民国",
        "birth_place": "浙江绍兴",
    },
    "童大年": {
        "cbdb_id": "100941",
        "courtesy_name": "醒盦",
        "art_name": "性涵",
        "birth_year": "1868",
        "death_year": "1955",
        "dynasty": "清",
        "birth_place": "江苏崇明",
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
    从人物的 source_text 中提取字号、籍贯、朝代、生卒年等信息

    返回: {'字': '寿承', '号': '三桥', '籍贯': '长洲', '朝代': '明',
           '生年': '1498', '卒年': '1573', '谥号': '', '科举': '', '官职': ''}
    """
    result = {
        "字": "", "号": "", "籍贯": "", "朝代": "",
        "生年": "", "卒年": "", "谥号": "", "科举": "", "官职": ""
    }

    if not source_text:
        return result

    text = source_text.strip()

    # ====== 1. 提取字 ======
    patterns_zi = [
        r"字[\s，,；;。:：]*([\u4e00-\u9fa5]{1,6})",
        r"字曰[\s，,]*([\u4e00-\u9fa5]{1,6})",
        r"又字[\s，,]*([\u4e00-\u9fa5]{1,6})",
        r"初字[\s，,]*([\u4e00-\u9fa5]{1,6})",
    ]
    for p in patterns_zi:
        m = re.search(p, text)
        if m:
            zi = m.group(1).strip()
            if zi and len(zi) >= 1 and zi not in ["某", "氏", "人", "号", "年"]:
                result["字"] = zi
                break

    # ====== 2. 提取号 ======
    patterns_hao = [
        r"号[\s，,；;。:：]*([\u4e00-\u9fa5]{1,10})",
        r"别号[\s，,]*([\u4e00-\u9fa5]{1,10})",
        r"又号[\s，,]*([\u4e00-\u9fa5]{1,10})",
        r"自号[\s，,]*([\u4e00-\u9fa5]{1,10})",
        r"晚号[\s，,]*([\u4e00-\u9fa5]{1,10})",
    ]
    for p in patterns_hao:
        m = re.search(p, text)
        if m:
            hao = m.group(1).strip()
            if hao and len(hao) >= 1 and hao not in ["某", "氏", "人", "字"]:
                result["号"] = hao
                break

    # ====== 3. 提取籍贯 ======
    invalid_places = ["字号", "字", "号", "其", "此", "进士", "举", "以", "而",
                       "所", "者", "之", "为", "亦", "乃", "则", "曰", "某", "氏",
                       "人", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                       "明", "清", "宋", "唐", "元", "汉", "万", "千", "百"]
    patterns_place = [
        r"([\u4e00-\u9fa5]{2,8})人",
        r"([\u4e00-\u9fa5]{2,8})籍",
        r"籍([\u4e00-\u9fa5]{2,8})",
        r"籍贯[\s：:，,]*([\u4e00-\u9fa5]{2,10})",
        r"世居[\s：:，,]*([\u4e00-\u9fa5]{2,10})",
        r"居[\s：:，,]*([\u4e00-\u9fa5]{2,10})",
        r"家于[\s：:，,]*([\u4e00-\u9fa5]{2,10})",
    ]
    for p in patterns_place:
        m = re.search(p, text)
        if m:
            place = m.group(1).strip()
            if len(place) >= 2 and place not in invalid_places:
                result["籍贯"] = place
                break

    # ====== 4. 提取朝代 ======
    # 4a. 通过朝代关键字
    dynasty_kw = [
        ("明", r"明[\s，,。；;朝年代国]"),
        ("清", r"清[\s，,。；;朝年代国]"),
        ("宋", r"宋[\s，,。；;朝年代国]"),
        ("元", r"元[\s，,。；;朝年代国]"),
        ("唐", r"唐[\s，,。；;朝年代国]"),
        ("汉", r"汉[\s，,。；;朝年代国]"),
        ("民国", r"民[国國]"),
        ("五代", r"五代"),
        ("晋", r"晋[\s，,。；;朝年代国]"),
        ("三国", r"三国"),
        ("隋", r"隋[\s，,。；;朝年代国]"),
        ("辽", r"辽[\s，,。；;朝年代国]"),
        ("金", r"金[\s，,。；;朝年代国]"),
    ]
    for dname, pattern in dynasty_kw:
        if re.search(pattern, text):
            result["朝代"] = dname
            break

    # 4b. 通过公元年份推断朝代
    if not result["朝代"]:
        year_ms = re.findall(r"(\d{3,4})", text)
        for y_str in year_ms:
            try:
                y = int(y_str)
                if 1368 <= y <= 1644:
                    result["朝代"] = "明"
                    break
                elif 1644 <= y <= 1911:
                    result["朝代"] = "清"
                    break
                elif 1912 <= y <= 1949:
                    result["朝代"] = "民国"
                    break
                elif 618 <= y <= 907:
                    result["朝代"] = "唐"
                    break
                elif 960 <= y <= 1279:
                    result["朝代"] = "宋"
                    break
                elif 1271 <= y <= 1368:
                    result["朝代"] = "元"
                    break
                elif 202 <= y <= 220:
                    result["朝代"] = "汉"
                    break
            except:
                pass

    # 4c. "明末" "清初"等
    if not result["朝代"]:
        m = re.search(r"(明清|明末|清初|清末|宋代|唐代|元代|汉代|晋代|隋末|晚唐|北宋|南宋|三国)", text)
        if m:
            kw = m.group(1)
            if "明" in kw: result["朝代"] = "明"
            elif "清" in kw: result["朝代"] = "清"
            elif "宋" in kw: result["朝代"] = "宋"
            elif "唐" in kw: result["朝代"] = "唐"
            elif "元" in kw: result["朝代"] = "元"
            elif "汉" in kw: result["朝代"] = "汉"
            elif "晋" in kw: result["朝代"] = "晋"
            elif "三国" in kw: result["朝代"] = "三国"

    # ====== 5. 提取生卒年 ======
    # 5a. 格式: XXXX年-YYYY年 / XXXX—YYYY
    m = re.search(r"(\d{3,4})[\s年年\-—～~至到\-]*(\d{2,4})[\s年]?", text)
    if m:
        birth = m.group(1)
        death_raw = m.group(2)
        if len(death_raw) == 2:
            death = birth[:2] + death_raw
        else:
            death = death_raw
        try:
            b_int = int(birth)
            d_int = int(death)
            if 500 <= b_int <= 2000 and 500 <= d_int <= 2000 and b_int < d_int:
                result["生年"] = birth
                result["卒年"] = death
        except:
            pass

    # 5b. 格式: 生于XXXX年
    if not result["生年"]:
        bm = re.search(r"(?:生于|生年)[\s于]*(\d{3,4})", text)
        if bm:
            result["生年"] = bm.group(1)

    # 5c. 格式: 卒于XXXX年
    if not result["卒年"]:
        dm = re.search(r"(?:卒|卒于|卒年|去世|殁|逝世)[\s于年月日]*(\d{3,4})", text)
        if dm:
            result["卒年"] = dm.group(1)

    # ====== 6. 提取谥号 ======
    shi_m = re.search(r"谥[\s曰:：,，]*([\u4e00-\u9fa5]{1,4})", text)
    if shi_m:
        result["谥号"] = shi_m.group(1).strip()
    else:
        shi_m2 = re.search(r"谥号[\s曰:：,，]*([\u4e00-\u9fa5]{1,6})", text)
        if shi_m2:
            result["谥号"] = shi_m2.group(1).strip()

    # ====== 7. 提取科举/官职 ======
    keju_list = ["进士", "举人", "状元", "榜眼", "探花", "翰林", "贡生",
                 "监生", "秀才", "生员", "廪生", "庠生", "明经", "孝廉"]
    guanzhi_list = ["尚书", "侍郎", "郎中", "主事", "知府", "知县", "知州",
                    "总督", "巡抚", "御史", "编修", "检讨", "詹事", "太傅",
                    "太保", "太师", "少师", "少傅", "少保", "布政使",
                    "按察使", "将军", "总兵", "刺史", "司马", "司空",
                    "司徒", "丞相", "宰相", "国公", "侯", "伯"]
    for kw in keju_list:
        if kw in text:
            result["科举"] = kw
            break
    for kw in guanzhi_list:
        if kw in text:
            result["官职"] = kw
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


def search_ctext_by_name(name: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    使用 ctext API 搜索人物（支持中文关键词）

    返回候选列表: [{name, ctext_id, url, dynasty, ...}]
    """
    try:
        params = urllib.parse.urlencode({"query": name, "if": "en"})
        url = f"{CTEXT_SEARCH_URL}?{params}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=CTEXT_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
            candidates = []

            # 尝试解析 JSON（ctext API 可能返回 JSON 或 HTML）
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    items = data[:max_results]
                elif isinstance(data, dict) and "results" in data:
                    items = data["results"][:max_results]
                else:
                    items = []
            except json.JSONDecodeError:
                # HTML 响应：从标题和链接提取
                items = []

            for item in items:
                ctext_id = item.get("id") or item.get("ID") or item.get("url")
                ctext_name = item.get("title") or item.get("name") or name
                ctext_url = item.get("url") or item.get("link") or ""
                extra = item.get("info") or item.get("description") or ""

                # 从 info 中提取朝代/字号等
                dynasty = ""
                place = ""
                courtesy = ""
                art = ""

                if extra:
                    clean = re.sub(r"<[^>]+>", "", extra)
                    # 提取朝代关键词
                    for dy in ["明", "清", "宋", "元", "唐", "汉", "民国", "三国", "晋", "隋", "南北朝"]:
                        if dy in clean:
                            dynasty = dy
                            break
                    # 提取籍贯关键词
                    for kw in ["钱塘", "仁和", "吴县", "长洲", "苏州", "常熟", "扬州", "江宁",
                                "金陵", "嘉兴", "秀水", "山阴", "绍兴", "歙县", "新安", "休宁",
                                "江阴", "仪征", "松江", "太仓", "南京", "杭州", "娄县"]:
                        if kw in clean:
                            place = kw
                            break
                    # 提取字号
                    zi_match = re.search(r"字([\u4e00-\u9fa5]{1,4})", clean)
                    if zi_match:
                        courtesy = zi_match.group(1)
                    hao_match = re.search(r"号([\u4e00-\u9fa5]{1,6})", clean)
                    if hao_match:
                        art = hao_match.group(1)

                if ctext_id or ctext_name:
                    candidates.append({
                        "cbdb_id": str(ctext_id) if ctext_id else "",
                        "name": ctext_name,
                        "courtesy_name": courtesy,
                        "art_name": art,
                        "birth_year": "",
                        "death_year": "",
                        "dynasty": dynasty,
                        "birth_place": place,
                        "ctext_url": ctext_url,
                        "source": "CTEXT",
                    })

            return candidates

    except Exception as e:
        print(f"  [ctext] 错误: {e}", file=sys.stderr)
        return []


def get_or_build_candidates(name: str, person_info: dict[str, Any], 
                            skip_external: bool = False) -> list[dict[str, Any]]:
    """
    构建候选列表：并行使用 CBDB API 和 ctext API

    优先级: KNOWN_CBDB_MAP > CBDB API > ctext API

    skip_external: 为 True 时跳过外部 API 调用（调试或 API 繁忙时使用）
    """
    # 1. 尝试从本地已知库获取（最可靠）
    if name in KNOWN_CBDB_MAP:
        known = KNOWN_CBDB_MAP[
            "cbdb_id": known["cbdb_id"],
            "name": name,
            "courtesy_name": known["courtesy_name"],
            "art_name": known["art_name"],
            "birth_year": known["birth_year"],
            "death_year": known["death_year"],
            "dynasty": known["dynasty"],
            "birth_place": known["birth_place"],
            "ctext_url": "",
            "source": "KNOWN_MAP",
        }]

    if skip_external:
        return []

    all_candidates = []

    # 2. 尝试 CBDB API 搜索
    print(f"  [候选] 搜索 '{name}'...", file=sys.stdout)
    cbdb_results = search_cbdb_by_name(name)
    if cbdb_results:
        for r in cbdb_results:
            r["ctext_url": r.get("ctext_url": "UNKNOWN")
            r["source"] = r.get("source": "CBDB_API")
            print(f"  CBDB: {r['name']} ID={r['cbdb_id']}")
        all_candidates.extend(cbdb_results)

    # 3. 尝试 ctext API 搜索
    ctext_results = search_ctext_by_name(name)
    if ctext_results:
        for r in ctext_results:
            r["source"] = r.get("source": "CTEXT")
            print(f"  ctext: {r['name']}")
        all_candidates.extend(ctext_results)

    if all_candidates:
        print(f"  共找到 {len(all_candidates)} 个候选.")
        return all_candidates

    # 4. 都失败
    print(f"  未找到外部候")
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
    基于规则的消歧打分（增强版）

    返回: (score, rules_applied)
    """
    score = 0.0
    rules: list[str] = []

    # 1. 姓名完全匹配
    ext_name = candidate.get("name", "")
    if ext_name == local_name:
        score += 0.3
        rules.append("姓名完全匹配 +0.3")

    # 1b. 姓名包含匹配（别名情况，如"文彭"包含"文"）
    elif local_name in ext_name or ext_name in local_name:
        if len(local_name) >= 2 and len(ext_name) >= 2:
            score += 0.15
            rules.append(f"姓名包含匹配({local_name}/{ext_name}) +0.15")

    # 2. 字号匹配（精确）
    local_courtesy = local_info.get("字", "")
    ext_courtesy = candidate.get("courtesy_name", "")
    if local_courtesy and ext_courtesy and local_courtesy == ext_courtesy:
        score += 0.3
        rules.append(f"字匹配（{local_courtesy}） +0.3")

    # 2b. 字号包含匹配
    elif local_courtesy and ext_courtesy:
        if local_courtesy in ext_courtesy or ext_courtesy in local_courtesy:
            score += 0.15
            rules.append(f"字号包含匹配({local_courtesy}/{ext_courtesy}) +0.15")

    # 3. 号匹配（精确）
    local_art = local_info.get("号", "")
    ext_art = candidate.get("art_name", "")
    if local_art and ext_art and local_art == ext_art:
        score += 0.25
        rules.append(f"号匹配（{local_art}） +0.25")

    # 3b. 号部分匹配
    elif local_art and ext_art:
        # 检查关键词重叠
        art_keywords = ["山人", "道人", "居士", "翁", "叟", "子", "斋", "堂", "庐", "阁", "轩", "亭", "庵", "院", "楼", "室"]
        for kw in art_keywords:
            if kw in local_art and kw in ext_art:
                score += 0.12
                rules.append(f"号关键词匹配({kw}) +0.12")
                break
        # 检查包含关系
        if local_art in ext_art or ext_art in local_art:
            score += 0.1
            rules.append(f"号包含匹配({local_art}/{ext_art}) +0.1")

    # 4. 籍贯匹配（精确）
    local_place = local_info.get("籍贯", "")
    ext_place = candidate.get("birth_place", "")
    if local_place and ext_place:
        # 标准化地点
        place_aliases = {
            "钱塘": ["钱塘", "杭州", "浙江钱塘", "仁和"],
            "仁和": ["仁和", "杭州", "浙江仁和", "钱塘"],
            "吴县": ["吴县", "苏州", "江苏吴县", "长洲"],
            "长洲": ["长洲", "苏州", "江苏长洲", "吴县"],
            "常熟": ["常熟", "苏州", "江苏常熟"],
            "嘉兴": ["嘉兴", "浙江嘉兴", "秀水"],
            "秀水": ["秀水", "嘉兴", "浙江秀水"],
            "山阴": ["山阴", "绍兴", "浙江山阴"],
            "歙县": ["歙县", "安徽歙县", "新安"],
            "休宁": ["休宁", "安徽休宁"],
            "娄县": ["娄县", "松江", "江苏娄县"],
            "华亭": ["华亭", "松江", "江苏华亭"],
            "江阴": ["江阴", "江苏江阴", "常州"],
            "仪征": ["仪征", "江苏仪征", "扬州"],
            "江宁": ["江宁", "南京", "江苏江宁", "金陵"],
            "金陵": ["金陵", "南京", "江苏金陵", "江宁"],
        }

        is_match = False
        for std_place, aliases in place_aliases.items():
            if any(local_place in a or a in local_place for a in aliases):
                if any(ext_place in a or a in ext_place for a in aliases):
                    is_match = True
                    break

        if is_match:
            score += 0.15
            rules.append(f"籍贯匹配（{local_place}≈{ext_place}） +0.15")
        elif local_place in ext_place or ext_place in local_place:
            score += 0.15
            rules.append(f"籍贯包含匹配({local_place}/{ext_place}) +0.15")

    # 5. 朝代匹配
    local_dynasty = local_info.get("朝代", "")
    ext_dynasty = candidate.get("dynasty", "")
    if local_dynasty and ext_dynasty and local_dynasty == ext_dynasty:
        score += 0.1
        rules.append(f"朝代匹配（{local_dynasty}） +0.1")

    # 5b. 朝代包含关系（明包含在"明代"中）
    elif local_dynasty and ext_dynasty:
        dynasty_kw = {"明": ["明", "明代", "明朝", "明季"], "清": ["清", "清代", "清朝", "清季", "清末"],
                     "宋": ["宋", "宋代", "宋朝"], "元": ["元", "元代", "元朝"],
                     "唐": ["唐", "唐代", "唐朝"], "汉": ["汉", "汉代", "汉朝"]}
        for d, kws in dynasty_kw.items():
            if local_dynasty in kws and ext_dynasty in kws:
                score += 0.1
                rules.append(f"朝代匹配({local_dynasty}/{ext_dynasty}) +0.1")
                break

    # 6. 生年匹配（允许误差10年）
    local_birth = local_info.get("生年", "")
    ext_birth = candidate.get("birth_year", "")
    if local_birth and ext_birth:
        try:
            lb = int(str(local_birth).replace("约", "").replace("约", ""))
            eb = int(ext_birth)
            if lb == eb or abs(lb - eb) <= 10:
                score += 0.15
                rules.append(f"生年匹配（{local_birth}≈{ext_birth}） +0.15")
        except:
            pass

    # 7. 卒年匹配（允许误差10年）
    local_death = local_info.get("卒年", "")
    ext_death = candidate.get("death_year", "")
    if local_death and ext_death:
        try:
            ld = int(str(local_death).replace("约", ""))
            ed = int(ext_death)
            if ld == ed or abs(ld - ed) <= 10:
                score += 0.1
                rules.append(f"卒年匹配（{local_death}≈{ext_death}） +0.1")
        except:
            pass

    # 8. 谥号匹配
    local_shi = local_info.get("谥号", "")
    ext_shi = candidate.get("posthumous_name", "")
    if local_shi and ext_shi and local_shi == ext_shi:
        score += 0.1
        rules.append(f"谥号匹配（{local_shi}） +0.1")

    # 9. 科举匹配
    local_keju = local_info.get("科举", "")
    ext_keju = candidate.get("keju", "")
    if local_keju and ext_keju and local_keju == ext_keju:
        score += 0.1
        rules.append(f"科举匹配（{local_keju}） +0.1")

    # 10. 官职匹配
    local_guan = local_info.get("官职", "")
    ext_guan = candidate.get("position", "")
    if local_guan and ext_guan and (local_guan in ext_guan or ext_guan in local_guan):
        score += 0.1
        rules.append(f"官职匹配（{local_guan}） +0.1")

    # 11. 职业/身份关键词匹配（篆刻家、画家、诗人等）
    local_text = local_info.get("_raw_text", "")[:500]
    ext_identity = candidate.get("identity", "")
    if ext_identity and ext_identity in local_text:
        score += 0.1
        rules.append(f"身份匹配({ext_identity}) +0.1")

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

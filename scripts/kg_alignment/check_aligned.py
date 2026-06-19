import sys
sys.path.insert(0, '.')
import json

from scripts.kg_alignment.align_entities import KNOWN_CBDB_MAP, extract_person_info

f = open('data/intermediate/entities.json', 'r', encoding='utf-8')
data = json.load(f)
f.close()
entities = data.get('entities', [])

print('=== KNOWN_CBDB_MAP 中的人 ===')
for n in sorted(KNOWN_CBDB_MAP.keys()):
    matches = [e for e in entities if e.get('name', '') == n]
    print(f'  {n}: 找到 {len(matches)} 个实体')
    for m in matches[:2]:
        src = m.get('source_text', '')[:80]
        info = extract_person_info(src, n)
        print(f'    - 源文本: {src}')
        print(f'    - 提取: {info}')

print()
print('=== aligned.ttl 内容摘要 ===')
with open('data/kg/aligned.ttl', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for line in lines[:50]:
    print(line.rstrip())

print()
print(f'  (共 {len(lines)} 行)')

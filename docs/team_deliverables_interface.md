# 团队交付接口约定

这个文件用于固定 A/B/C/D 四位成员的交付目录、文件名和最小字段要求。后续整合阶段默认只认这里定义的路径。

## 总原则

- 不要随意改文件名。
- 如果临时需要新文件，先和成员 D 确认，再补进这个文档。
- 最终正式图谱格式必须是 `RDF Turtle`，JSON 只作为中间结果。
- 所有路径都相对于项目根目录 `kg_agent_app/`。

## 成员 A：数据准备与文本处理

交付位置：

- `data/source/raw_text/`
- `data/source/clean_text/`
- `data/source/chapter_split.json`
- `data/source/person_passages.json`

说明：

- `raw_text/`：放 OCR 或 PDF 转文本后的原始文本文件，可按章节拆成多个 `.txt`
- `clean_text/`：放清洗后的文本文件，命名尽量与原始文本对应
- `chapter_split.json`：记录章节、页码或段落切分结果
- `person_passages.json`：按人物归并的段落样本，供成员 B 抽取使用

`chapter_split.json` 最小结构示例：

```json
[
  {
    "chapter_id": "chapter_001",
    "title": "示例章节",
    "source_file": "yinrenzhuan_part1.txt",
    "start_offset": 0,
    "end_offset": 1200,
    "text": "这里放该章节或片段的文本"
  }
]
```

`person_passages.json` 最小结构示例：

```json
[
  {
    "person_name": "文彭",
    "source_chapter_id": "chapter_001",
    "passage_id": "passage_001",
    "text": "文彭，字寿承，号三桥……"
  }
]
```

## 成员 B：知识抽取

交付位置：

- `data/intermediate/entities.json`
- `data/intermediate/relations.json`
- `data/intermediate/extraction_prompts.md`
- `data/intermediate/evaluation_samples.json`

说明：

- `entities.json`：命名实体和属性抽取结果
- `relations.json`：人物关系抽取结果
- `extraction_prompts.md`：抽取提示词、模板、few-shot 或规则说明
- `evaluation_samples.json`：人工评测样本、抽取误差分析样本

`entities.json` 最小结构示例：

```json
[
  {
    "entity_id": "person_wen_peng",
    "name": "文彭",
    "type": "Person",
    "source_passage_id": "passage_001",
    "attributes": {
      "courtesy_name": ["寿承"],
      "art_name": ["三桥"],
      "birth_year": "",
      "death_year": ""
    }
  }
]
```

`relations.json` 最小结构示例：

```json
[
  {
    "relation_id": "rel_001",
    "subject": "文徵明",
    "predicate": "父子",
    "object": "文彭",
    "relation_type": "亲属",
    "source_passage_id": "passage_001",
    "evidence": "文彭，字寿承，号三桥，文徵明长子。"
  }
]
```

## 成员 C：图谱构建与外部对齐

交付位置：

- `data/kg/schema.ttl`
- `data/kg/core.ttl`
- `data/kg/aligned.ttl`
- `data/kg/alignment_rules.md`

说明：

- `schema.ttl`：RDF/RDFS 模式层，本体、类、属性、命名空间
- `core.ttl`：根据《印人传》抽取出的核心图谱
- `aligned.ttl`：与 CBDB / CText 对齐和补充后的图谱
- `alignment_rules.md`：实体消歧、对齐规则和字段映射说明

成员 D 当前工具层默认预留的占位属性包括：

- `ex:hasCourtesyName`
- `ex:hasArtName`
- `ex:birthYear`
- `ex:deathYear`
- `ex:hasTeacher`
- `ex:hasRelative`
- `ex:relativeRelationType`
- `ex:hasFriend`
- `ex:belongsToSchool`
- `ex:foundsSchool`

如果成员 C 最终命名不同，必须把最终属性表同步给成员 D 做最后联调替换。

## 成员 D：查询问答与前端

交付位置：

- `src/tools.py`
- `data/examples/fewshot_sparql.md`
- `templates/index.html`
- `static/styles.css`
- `docs/demo_script.md`

说明：

- `src/tools.py`：固定工具函数、SPARQL 模板查询
- `data/examples/fewshot_sparql.md`：few-shot SPARQL 示例集
- `templates/index.html`：网页前端
- `static/styles.css`：页面样式
- `docs/demo_script.md`：答辩展示脚本、演示顺序、异常兜底话术

## 健康检查

后端健康接口：

- `GET /api/health`

它会返回：

- Turtle 文件是否存在
- A/B/C/D 各自约定交付物是否已落到固定位置
- 当前接口文档路径

## 联调要求

- A 先保证文本和人物段落样本可用
- B 再保证实体和关系 JSON 可读、字段不乱改
- C 最后统一 Turtle 模式和属性命名
- D 在收到 C 的属性命名终稿后，统一修改查询工具和 few-shot 示例

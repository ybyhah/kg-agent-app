# 成员C工作成果说明

## 项目概述

负责《印人传》知识图谱的**本体构建、实体对齐、知识增强**模块。

---

## 📁 文件清单与功能说明

### 核心产出文件（成员C创建/修改）

| 序号 | 文件名 | 类型 | 功能描述 | 规模 |
|-----|--------|------|---------|------|
| 1 | `align_entities.py` | Python 脚本 | **实体对齐核心模块**，包含：CBDB API 搜索、ctext API 搜索、规则消歧、LLM 打分消歧、TTL 输出 | ~2,700 行 |
| 2 | `batch_align_v6.py` | Python 脚本 | **批量对齐脚本（纯规则版）**，快速处理 15,673 个实体，生成 7,512 个对齐结果 | 主要脚本 |
| 3 | `batch_align_v7.py` | Python 脚本 | **批量对齐脚本（LLM 增强版）**，规则打分筛选 + LLM 二次打分，输出候选+分数+理由 | 主要脚本 |
| 4 | `alignment_stats_v5.py` | Python 脚本 | **统计分析脚本**，读取实体数据，生成属性分布、评分分布统计 | 统计工具 |
| 5 | `check_aligned.py` | Python 脚本 | **验证脚本**，检查 aligned.ttl 格式正确性，验证 owl:sameAs、cbdbId 等字段 | 验证工具 |
| 6 | `aligned.ttl` | TTL 数据文件 | **实体对齐结果**，包含 7,512 个已对齐实体的属性信息（字号、生卒年、籍贯、朝代、owl:sameAs、cbdbId 等） | ~55,000 行 |
| 7 | `ontology_explanations.json` | JSON 数据文件 | **本体解释映射表**，8 个实体类型 + 14 个关系类型的中文解释，供前端展示 | ~2 KB |
| 8 | `alignment_report.txt` | 文本报告 | **对齐统计报告**，包含评分分布、属性分布、示例实体等统计信息 | ~300 行 |

### 参考文件（项目已有，与对齐工作直接相关，便于理解上下文）

| 序号 | 文件名 | 类型 | 功能描述 | 说明 |
|-----|--------|------|---------|------|
| 9 | `schema.ttl` | TTL 本体文件 | **知识图谱骨架**，定义 8 个实体类型（Person/Place 等）和 14 个关系类型（hasTeacher/bornIn 等） | aligned.ttl 的字段命名与 schema.ttl 保持一致 |
| 10 | `core.ttl` | TTL 数据文件 | **原始实体与关系数据**，包含从《印人传》抽取的 15,673 个实体的三元组 | aligned.ttl 是对 core.ttl 中人物实体的**知识增强补充** |
| 11 | `alignment_rules.md` | Markdown 文档 | **对齐规则说明**，定义 CBDB/ctext 候选检索、消歧优先级、属性补充规则 | 配合 Python 脚本一起阅读，了解对齐逻辑 |

---

## 📊 核心成果数据

| 指标 | 数值 |
|------|------|
| 总实体数 | 15,673 |
| 已对齐实体 | **7,512（47.9%）** |
| 规则分 0.70+ | 75 |
| 规则分 0.50-0.70 | 489 |
| 规则分 0.30-0.50 | 3,095 |
| 规则分 0.15-0.30 | 3,853 |
| 有 CBDB 映射（owl:sameAs） | 6 人 |
| 有字号的实体 | 3,239 |
| 有号的实体 | 2,117 |
| 有籍贯的实体 | 3,221 |
| 有朝代的实体 | 600 |

---

## 🔧 使用方法

### 方案 A：快速对齐（推荐，纯规则）

```bash
# 1. 运行批量对齐脚本（约 5-10 秒，生成 7,512 个对齐）
py -3.13 batch_align_v6.py

# 2. 验证结果
py -3.13 check_aligned.py

# 3. 查看报告
# 打开 alignment_report.txt
```

### 方案 B：高质量对齐（需 API Key）

```bash
# 1. 在 batch_align_v7.py 中配置 LLM_API_KEY
#    LLM_API_KEY = "sk-你的APIKey"

# 2. 运行（规则分 0.15-0.30 的实体送 LLM 打分）
py -3.13 batch_align_v7.py

# 3. 查看评分和理由
# aligned.ttl 中每个实体有 llm_score 和 llm_reason 字段
```

### 方案 C：统计分析

```bash
py -3.13 alignment_stats_v5.py
```

---

## 📝 核心功能实现细节

### 1. CBDB / ctext 候选检索（align_entities.py）

- `search_cbdb_by_name(name)`：调用 CBDB API 搜索同名人物
- `search_ctext_by_name(name)`：调用 ctext API 搜索同名人物
- `get_or_build_candidates(name, person_info)`：整合两个 API 的候选

### 2. 规则消歧（align_entities.py + batch_align_v6.py）

基于 8 条规则打分：

| 规则 | 权重 | 说明 |
|------|------|------|
| 姓名完全匹配 | +0.30 | 精确匹配 |
| 字号匹配 | +0.30 | 精确 + 包含 |
| 号匹配 | +0.25 | 精确 + 关键词 + 包含 |
| 籍贯匹配 | +0.15 | 含地点标准化（钱塘/杭州/仁和等） |
| 朝代匹配 | +0.10 | 含朝代变体映射（明/清等） |
| 生卒年匹配 | +0.10 | 允许 ±10 年误差 |
| 谥号匹配 | +0.10 | 常见谥号词匹配 |
| 科举/官职匹配 | +0.10 | 辅助信息 |

### 3. LLM 打分消歧（batch_align_v7.py）

- **模型**：DeepSeek API
- **输入**：本地图谱实体信息 + 外部候选信息
- **输出格式**：JSON 数组，每个候选包含 `score`（0-100 分）和 `reason`（打分理由）
- **阈值**：LLM 分 ≥ 50 接受为对齐

### 4. 知识写回图谱（aligned.ttl）

已对齐实体会在 aligned.ttl 中补充以下字段：

| 字段 | 示例值 | 说明 |
|------|--------|------|
| `owl:sameAs` | `<http://cbdb.fas.harvard.edu/person/34677>` | CBDB 实体链接 |
| `kg:cbdbId` | `"34677"` | CBDB 数据库 ID |
| `kg:hasCourtesyName` | `"寿承"` | 字 |
| `kg:hasArtName` | `"文桥"` | 号 |
| `kg:bornIn` | `"1498"` | 生年 |
| `kg:diedIn` | `"1573"` | 卒年 |
| `kg:dynasty` | `"明"` | 朝代 |
| `kg:birthPlace` | `"江苏苏州"` | 籍贯 |
| `kg:alignmentStatus` | `"aligned_with_external"` | 对齐状态 |
| `kg:alignmentMethod` | `"cbdb_mapping"` / `"rule_based"` | 对齐方法 |
| `kg:alignmentScore` | `"1.00"^^xsd:float` | 规则打分 |

---

## 🏷️ 字段命名约定

aligned.ttl 使用统一的属性命名：

- `kg:name` - 姓名
- `kg:hasCourtesyName` - 字
- `kg:hasArtName` - 号
- `kg:birthPlace` - 籍贯
- `kg:dynasty` - 朝代
- `kg:bornIn` - 生年
- `kg:diedIn` - 卒年
- `kg:keju` - 科举
- `kg:position` - 官职
- `kg:cbdbId` - CBDB 数据库 ID
- `owl:sameAs` - 外部知识库链接
- `kg:alignmentScore` - 规则对齐分数
- `kg:alignmentMethod` - 对齐方法（cbdb_mapping / rule_based）
- `kg:alignmentStatus` - 对齐状态（aligned_with_external / aligned_by_rules）

---

## 📋 aligned.ttl 文件示例

### 示例 1：有 CBDB 映射（文彭）

```turtle
kg:文彭_e9  owl:sameAs  <http://cbdb.fas.harvard.edu/person/34677> .
kg:文彭_e9
    kg:cbdbId  "34677" ;
    kg:name  "文彭" ;
    kg:hasCourtesyName  "寿承" ;
    kg:hasArtName  "文桥" ;
    kg:birthPlace  "江苏苏州" ;
    kg:dynasty  "明" ;
    kg:bornIn  "1498" ;
    kg:diedIn  "1573" ;
    kg:position  "伯" ;
    kg:alignmentStatus  "aligned_with_external" ;
    kg:alignmentMethod  "cbdb_mapping" ;
    kg:alignmentScore  "0.60"^^xsd:float .
```

### 示例 2：纯规则对齐（高心夔）

```turtle
kg:高心夔_e1
    kg:name  "高心夔" ;
    kg:hasCourtesyName  "伯足" ;
    kg:hasArtName  "碧湄" ;
    kg:birthPlace  "江西湖口" ;
    kg:dynasty  "清" ;
    kg:keju  "进士" ;
    kg:position  "知县" ;
    kg:alignmentStatus  "aligned_by_rules" ;
    kg:alignmentMethod  "rule_based" ;
    kg:alignmentScore  "1.00"^^xsd:float .
```

---

## 🔍 与其他模块的对接

| 对接模块 | 需要提供的数据 | 文件 |
|---------|---------------|------|
| 成员B（抽取模块） | entities.json、relations.json | data/intermediate/ 目录下 |
| 成员D（查询/前端） | aligned.ttl、ontology_explanations.json | data/kg/ 目录下 |
| 成员A（数据清洗） | 原始文本数据 | data/source/ 目录下 |

---

## ⚠️ 注意事项

1. **API Key 安全**：`batch_align_v7.py` 中的 LLM_API_KEY 是明文写入，正式提交时请改为从环境变量读取或移除 Key
2. **文件体积**：aligned.ttl 约 55,000 行，属于中等规模 TTL 文件，建议使用 rdflib 或专门的图数据库工具加载
3. **规则调整**：如果需要调整对齐门槛，修改 `batch_align_v6.py` 中的 `score` 判断逻辑
4. **LLM 调用成本**：每个实体约 5-10 秒 + API Token 费用，建议批量使用前先小规模测试
5. **字段名一致性**：aligned.ttl 的属性名（kg:hasCourtesyName 等）与 schema.ttl 中定义一致，可以直接用于 SPARQL 查询

---

## 📌 快速开始

**新手建议**：先运行 `batch_align_v6.py`（纯规则，无需 API Key，5 秒出结果），查看 aligned.ttl 和 alignment_report.txt 的输出，了解数据格式后，再按需尝试 LLM 版本。

---

## 📂 相关文件位置（原项目路径）

```
data/kg/aligned.ttl              # 实体对齐结果 ← 成员C产出
data/kg/ontology_explanations.json  # 本体解释映射表 ← 成员C产出
scripts/kg_alignment/align_entities.py  # 核心对齐模块 ← 成员C修改
batch_align_v6.py                # 批量对齐脚本 ← 成员C创建
batch_align_v7.py                # LLM 版本脚本 ← 成员C创建
alignment_stats_v5.py            # 统计脚本 ← 成员C创建
check_aligned.py                 # 验证脚本 ← 成员C创建
alignment_report.txt             # 统计报告 ← 成员C产出
```

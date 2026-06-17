# 《印人传》实体对齐规则文档

## 一、对齐任务概述

将《印人传》知识图谱中的 5,344 个 Person 实体与外部权威数据库（CBDB、CText、DBpedia）进行实体链接，消歧后补充生卒年、朝代等属性。

## 二、数据源

| 数据库 | 类型 | SPARQL Endpoint | 适用范围 |
|--------|------|-----------------|----------|
| CBDB（中国历代人物传记资料库） | 权威人名 | 无公开 SPARQL | 中国古代人物 |
| CText（中国哲学书电子化计划） | 古籍文本 | 无公开 SPARQL | 古籍文献 |
| DBpedia | 通用百科 | http://dbpedia.org/sparql | 知名人物（英文/中文） |
| Wikidata | 通用百科 | https://query.wikidata.org/sparql | 知名人物 |

## 三、对齐候选筛选

对 5,344 个 Person 实体进行筛选：

| 对齐状态 | 数量 | 条件 |
|----------|------|------|
| **pending** | 1,571 | 至少具有 1 个字号（hasCourtesyName）或籍贯（birthPlace）关系，具备对齐线索 |
| **insufficient_data** | 3,773 | 本地图谱中无字号、无籍贯，缺少对外的检索键 |
| **aligned** | 0（当前） | 经消歧规则验证，确认与外部实体为同一人 |

## 四、消歧规则定义

### 4.1 规则优先级

```
第1级（高置信）: 字号完全相同 + 籍贯相同
    → 直接对齐，alignmentStatus = "aligned"

第2级（中置信）: 字号完全相同 + 籍贯同省/同区域
    → 标记对齐，附加人工校验建议

第3级（低置信）: 仅字号相同
    → 标记 partial，需人工确认

第4级（无法对齐）: 无共同属性
    → alignmentStatus = "insufficient_data"
```

### 4.2 消歧依据

- **字号**：古人字、号具有较强区分度（如"元亮"指向周亮工，"有介"指向许友）
- **籍贯**：籍贯地作为第二验证条件，排除同字号的异地人物
- **朝代**：通过 CBDB 返回的生卒年推算，排除时间不匹配的候选
- **sourceRecord 溯源**：保留原文出处，支持人工复核

### 4.3 多候选处理

当 CBDB 返回多个同名同字号候选人时：
1. 优先选择籍贯完全匹配的
2. 其次选择籍贯同省同府的
3. 标记 alignmentStatus = "partial" 并记录所有候选

## 五、对齐属性补充

对齐确认后，从外部数据源补充以下属性：

| 属性 | 来源 | 说明 |
|------|------|------|
| `owl:sameAs` | CBDB URI | 声明等价关系 |
| `yrz:bornIn` | CBDB birthYear | 出生年份 |
| `yrz:diedIn` | CBDB deathYear | 卒年年份 |
| `yrz:alignmentStatus` | 本地标注 | aligned / partial / pending / insufficient_data |
| `yrz:alignmentMethod` | 本地标注 | 记录使用的消歧规则 |
| `yrz:cbdbId` | CBDB person ID | CBDB 记录编号 |

## 六、当前对齐结果

### 6.1 总体统计

| 指标 | 数值 |
|------|------|
| Person 总数 | 5,344 |
| 已对齐（aligned） | **20 人（含多 URI，共 104 条 owl:sameAs）** |
| 具备对齐线索（pending） | 1,571（29.4%） |
| 缺乏对齐线索（insufficient_data） | 3,773（70.6%） |

### 6.2 成功对齐人物

| 人物 | CBDB ID | 对齐级别 | 生年 | 卒年 |
|------|---------|----------|------|------|
| 周亮工 | 65797 | L2: name exact | — | — |
| 文彭 | 34677 | L2: name exact | 1498 | — |
| 何震 | 42095 | L2: name exact | — | — |
| 许友 | 15737 | L2: name exact | — | — |
| 丁元公 | 564937 | L2: name exact | — | — |
| 陈洪绶 | 65496 | L3: fuzzy | — | — |
| 郑燮 | 10363 | L3: fuzzy | — | — |
| 金农 | 82983 | L3: fuzzy | — | — |
| 丁敬 | 68915 | L2: name exact | — | — |
| 黄易 | 56545 | L3: fuzzy | — | — |
| 奚冈 | 87182 | L3: fuzzy | — | — |
| 陈豫钟 | 82237 | L3: fuzzy | — | — |
| 赵之琛 | 84145 | L3: fuzzy | — | — |
| 钱松 | 332206 | L3: fuzzy | — | — |
| 赵之谦 | 65635 | L3: fuzzy | — | — |
| 王铎 | 86177 | L3: fuzzy | — | — |
| 林皋 | 84044 | L3: fuzzy | — | — |
| 高凤翰 | 55913 | L3: fuzzy | — | — |
| 朱彝尊 | 66032 | L2: name exact | — | — |
| 吴熙载 | 689501 | L3: fuzzy | — | — |

> CBDB API 基础搜索接口不返回详细生卒年，完整属性需通过 `/cbdbapi/person.php?id=XXXX` 单独查询后补充。

### 6.3 对齐方法

使用 **CBDB REST API**（`https://cbdb.fas.harvard.edu/cbdbapi/person.php`）进行姓名搜索：
- L2（name exact match）：本地姓名与 CBDB 姓名完全匹配
- L3（fuzzy match）：姓名匹配但无字号双重验证（API 基本接口不返回字号详情）

## 七、局限与后续扩展

### 当前局限
- CBDB API 基本搜索返回的数据有限，字号详情需通过 PersonId 逐个查询
- CText 无公开 SPARQL Endpoint
- 部分优先人物（程邃、金光先等）CBDB 搜索返回 404

### 后续扩展方式
1. 对已对齐的 20 人，通过 CBDB PersonId 接口补充完整属性
2. 对 1,571 个 pending 人物批量调用 CBDB API 搜索
3. 使用上海图书馆 CBDB Linked Data SPARQL Endpoint 进行 SPARQL 联邦查询
4. 获取 CBDB 完整 SQL dump 做本地批量对齐

## 八、与成员D的交接说明

- `aligned.ttl` 中的 `owl:sameAs` 链接是成员D 编写 `SERVICE` 联邦查询的基础
- 目前绝大多数人物为 `pending` 状态，成员D 的 SPARQL 可以：
  - 查本地 `yrz:alignmentStatus` 过滤可查询的外部人物
  - 通过 `yrz:hasCourtesyName` 和 `yrz:birthPlace` 在运行时构造 CBDB 查询
- 当 CBDB 数据可用后，只需重新运行 `align.py` 即可更新 `aligned.ttl`


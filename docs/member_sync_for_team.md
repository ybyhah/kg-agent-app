# KG Agent 队员同步说明

仓库地址：

- `https://github.com/ybyhah/kg-agent-app.git`

当前分支：

- `main`

当前已推送版本：

- `71501a0`
- 提交说明：`feat: 完善问答链路与前端展示`

## 1. 当前项目状态

现在仓库里已经有可运行的整合骨架，主要包括：

- Flask 前端页面
- 固定查询工具层
- LangGraph 工作流骨架
- few-shot SPARQL 生成链路
- 图结构分析页面
- 关系网络可视化骨架
- 工具说明和课程依据展示区

## 2. 队员拉取方式

如果你们是第一次拿代码：

```bash
git clone https://github.com/ybyhah/kg-agent-app.git
```

如果已经有仓库：

```bash
git pull origin main
```

## 3. 本地运行方式

进入项目目录后：

```bash
pip install -r requirements.txt
python app.py
```

浏览器访问：

- `http://127.0.0.1:5000`

## 4. 当前对接约定

### 成员 A

- 文本清洗结果放到 `data/source/raw_text/` 和 `data/source/clean_text/`
- 章节切分放到 `data/source/chapter_split.json`
- 人物段落样本放到 `data/source/person_passages.json`

### 成员 B

- 实体抽取结果放到 `data/intermediate/entities.json`
- 关系抽取结果放到 `data/intermediate/relations.json`
- 抽取提示词和样例说明放到 `data/intermediate/extraction_prompts.md`
- 评测样例放到 `data/intermediate/evaluation_samples.json`

### 成员 C

- 本体和 schema 放到 `data/kg/schema.ttl`
- 核心图谱放到 `data/kg/core.ttl`
- 对齐补充图谱放到 `data/kg/aligned.ttl`
- 对齐规则放到 `data/kg/alignment_rules.md`

### 成员 D

- 查询工具：`src/tools.py`
- 工作流：`src/workflow.py`、`src/tool_calling_workflow.py`
- few-shot 示例：`data/examples/fewshot_sparql.md`
- 前端页面：`templates/index.html`
- 页面样式：`static/styles.css`

## 5. 队员需要注意

- 不要随意改文件名和路径
- 正式图谱最终以 `RDF Turtle` 为准
- `.env` 不要提交到仓库
- 如果成员 C 调整了本体属性名，要同步修改工具层和 few-shot 示例

## 6. 现在可以直接做的事

- 拉取最新代码查看页面
- 按固定路径补 A/B/C 的交付
- 继续完善查询工具、SPARQL 示例和前端展示
- 用浏览器直接验证 `http://127.0.0.1:5000`


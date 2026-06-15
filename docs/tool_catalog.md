# 大模型可调用工具说明

本文件对应大作业评分项“构建大模型能够使用的工具（10 分）”。

## 设计原则

- 保留 `src/tools.py` 作为底层 SPARQL 查询实现层。
- 在其上新增 `src/agent_tools.py` 作为面向大模型 / LangGraph 工作流的工具封装层。
- 每个工具统一提供：
  - 工具名
  - 功能说明
  - 参数说明
  - 返回结果说明
  - 对应 SPARQL
  - 课程依据

## 课程依据

### 2026新1.pdf

- 第 17 页：课程总览中包含 `Knowledge Extraction`、`Knowledge Extraction using Langchain`、`User Query Parsing`
- 第 18 页：课程总览中包含 `RDF`、`RDF Turtle Serialization`、`Model Building with RDFS`
- 第 19 页：课程总览中包含 `Querying RDF with SPARQL`、`Knowledge Graph Programming`、`Knowledge Graph Agent`
- 第 22 页：项目展示模块包含 `Entity Linking and Knowledge Complement`、`Question Answering System with Langgraph`、`Web Interface and Visualization`

### 2026新2.pdf

- 第 57 页：LangChain 中模型可以发起 `tool calls`
- 第 58 页：`Tool Message` 用于将工具执行结果返回给模型
- 第 60 页：`Structured Output` 使用 Pydantic schema 约束输出
- 第 65 页：`User Query Parsing` 是 KBQA 的核心挑战之一
- 第 68 页：`Semantic parser` 将自然语言问题转为可执行查询，如 SPARQL
- 第 80 页：课程练习要求使用 LangChain 解析用户问句并抽取命名实体

### 2026新3.pdf

- 第 2 页：`RDF`、`Turtle Serialization`、`RDFS` 是图谱表示基础

### 2026新4.pdf

- 第 2 页：课程主题为 `Querying RDFS with SPARQL`
- 第 155 页：工具需要提供清晰的输入输出，供模型调用
- 第 157 页：`@tool` 的 docstring 与 type hints 决定工具说明和输入 schema
- 第 158 页：工具需要 `bind_tools`
- 第 159 页：`ToolNode` 负责在 LangGraph 工作流中执行工具
- 第 160 页：`KG-agent with Langgraph` 组件包括 `State / Nodes / Edges / Tools / Workflow`
- 第 161 页：大项目要求“使用 LLM based agent 解析用户问句，并用 tools 搜索答案”

## 当前工具清单

- `get_person_labels`：查询人物候选实体
- `get_courtesy_name`：查询人物字
- `get_art_name`：查询人物号
- `get_birth_death`：查询人物生卒年
- `get_teacher_relations`：查询师承关系
- `get_family_relations`：查询亲属关系
- `get_social_relations`：查询交游关系
- `get_school_membership`：查询所属流派
- `get_school_founder`：查询流派开创者
- `get_pair_relations`：查询两人关系
- `get_related_people`：查询关联人物网络
- `run_raw_sparql`：执行高级 SPARQL

## 工程落点

- 工具封装：`src/agent_tools.py`
- 底层 SPARQL 查询：`src/tools.py`
- 工作流：`src/workflow.py`
- 工具说明接口：`/api/tools`
- 前端展示区：`templates/index.html`


# KG Agent 项目骨架

这个目录是面向成员 D 的最终整合骨架，用来提前搭好问答系统、SPARQL 查询层和前端展示页面，后续再接入其他成员的成果。

## 目标

为下面这些内容提供稳定的整合入口：

- 成员 A 的文本预处理结果
- 成员 B 的知识抽取 JSON 结果
- 成员 C 的 RDF Turtle 图谱结果
- 成员 D 的查询、工作流编排和前端整合

## 推荐的队友交付文件

- `data/source/raw_text/`
- `data/source/clean_text/`
- `data/source/chapter_split.json`
- `data/source/person_passages.json`
- `data/intermediate/entities.json`
- `data/intermediate/relations.json`
- `data/intermediate/extraction_prompts.md`
- `data/intermediate/evaluation_samples.json`
- `data/kg/schema.ttl`
- `data/kg/core.ttl`
- `data/kg/aligned.ttl`
- `data/kg/alignment_rules.md`

详细字段约定见：

- `docs/team_deliverables_interface.md`

## 当前已经包含的内容

- Flask 应用入口
- 本地图谱加载层
- 固定查询工具层
- few-shot SPARQL 生成链路
- LangGraph 工作流骨架
- 可选的大模型增强层
- 普通问答和高级 SPARQL 页面
- 工具说明与课程依据展示区
- 人物关系网络可视化骨架

## 当前支持的 LLM 模式

- `disabled`
- `local_transformers`
- `openai`

当前 OpenAI 模式负责：

1. 工具不足时生成 SPARQL
2. 查询结果后生成自然语言回答
3. SPARQL 失败时做 fallback

当前还没有直接做到真正的 function calling 工具调用链；后续升级路径见：

- `docs/openai_upgrade_path.md`

## 运行步骤

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 把 TTL 文件放到 `data/kg/`

3. 如需使用 OpenAI，新建本地 `\.env`

示例：

```env
OPENAI_API_KEY=你的key
KG_AGENT_LLM_MODE=openai
KG_AGENT_OPENAI_MODEL=gpt-5.5
```

4. 启动项目
```bash
python app.py
```

5. 打开
```text
http://127.0.0.1:5000
```

## Git/GitHub 协作建议

- 提交前先确认页面还能打开
- 不要提交 `.env`、缓存文件和本地调试产物
- 中间 JSON 和正式 TTL 建议通过固定文件名接入，不要每个人随意改名
- 详细协作方式见 `GIT_WORKFLOW.md`

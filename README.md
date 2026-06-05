# KG Agent 项目骨架

这个目录是面向成员 D 的最终整合骨架，用来提前搭好问答系统、SPARQL 查询层和前端展示壳子，后续再接入其他成员的成果。

## 目标

为下面这些内容提供稳定的整合入口：

- 成员 A 的文本预处理结果
- 成员 B 的知识抽取 JSON 结果
- 成员 C 的 RDF Turtle 图谱结果
- 成员 D 的查询、工作流编排和前端整合

## 推荐的队友交付文件

- `data/intermediate/entities.json`
- `data/intermediate/relations.json`
- `data/intermediate/attributes.json`
- `data/kg/schema.ttl`
- `data/kg/core.ttl`
- `data/kg/aligned.ttl`

## 运行步骤

1. 安装 `requirements.txt` 里的依赖
2. 把 TTL 文件放到 `data/kg/`
3. 执行 `python app.py`
4. 打开 `http://127.0.0.1:5000`

## Git/GitHub 协作建议

- 提交前先确认页面还能打开
- 不要提交 `.env`、缓存文件和本地调试产物
- 中间 JSON 和正式 TTL 建议通过固定文件名接入，不要每个人随意改名
- 详细协作方式见 `GIT_WORKFLOW.md`

## 当前已经包含的内容

- Flask 应用入口
- SPARQL 工具封装
- 本地图谱加载层
- 简单的查询工作流路由
- 普通问答和高级 SPARQL 页面
- 成员 D 的整合说明

## 当前还没有包含的内容

- 真实的大模型接入
- 队友最终交付的数据
- 最终版 SPARQL 模板
- 最终版关系网络可视化

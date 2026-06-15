# 兼容 API 接入与升级路径

当前项目已经支持：

- `KG_AGENT_LLM_MODE=disabled`
- `KG_AGENT_LLM_MODE=local_transformers`
- `KG_AGENT_LLM_MODE=openai`

其中 `KG_AGENT_LLM_MODE=openai` 现在按 OpenAI 兼容 API 处理，可直接接 DeepSeek，默认模型为 `deepseek-v4-flash`。

## 当前兼容 API 模式负责的能力

1. 在固定工具不足时，基于 few-shot 示例生成 SPARQL
2. 在 SPARQL 查询成功后，根据查询结果生成自然语言回答
3. 在 SPARQL 生成失败或执行失败后，提供谨慎的 fallback 回答
4. 在简单问题命中时，走 `LLM -> ToolNode -> ToolMessage -> LLM` 的工具调用链

## 当前阶段的定位

这一版仍然以“本地知识图谱”为核心知识源：

- 本体与事实：`schema.ttl`、`core.ttl`、`aligned.ttl`
- 大模型职责：问句解析增强、工具选择、SPARQL 生成、结果组织、失败兜底

也就是说，大模型不是主知识库，而是工作流中的解析和表达层。

## 当前主链路

1. 用户提问
2. LLM 判断是否可以由固定工具直接回答
3. 若可回答：调用工具 -> `ToolNode` 执行 -> 工具结果回模型 -> 模型组织最终回答
4. 若不可直接回答：LLM / few-shot 生成 SPARQL -> 执行 -> LLM 根据结果回答
5. 若 SPARQL 失败：进入 fallback

## 当前为什么保留兼容 API 封装

- 课程要求强调 LangGraph、工具调用、SPARQL 生成和问答链路
- OpenAI 官方 SDK 兼容多家模型服务，便于保持主链路不变
- 切换 DeepSeek 时，只需要改配置，不需要推翻现有 `ToolNode` 和工作流结构

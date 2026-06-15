# OpenAI 接入与后续升级路径

当前项目已经支持：

- `KG_AGENT_LLM_MODE=disabled`
- `KG_AGENT_LLM_MODE=local_transformers`
- `KG_AGENT_LLM_MODE=openai`

当前 OpenAI 模式负责三件事：

1. 在固定工具不足时，基于 few-shot 示例生成 SPARQL
2. 在 SPARQL 查询成功后，根据查询结果生成自然语言回答
3. 在 SPARQL 生成失败或执行失败后，提供谨慎的 fallback 回答

## 当前阶段的定位

这一版仍然以“本地知识图谱”为核心知识源：

- 本体与事实：`schema.ttl`、`core.ttl`、`aligned.ttl`
- 大模型职责：问句解析增强、SPARQL 生成、结果组织、失败兜底

也就是说，大模型不是主知识库，而是工作流中的解析和表达层。

## 后续升级到 function calling 的结构

后续如果要更贴课程里 `Tool / bind_tools / ToolNode` 的讲法，建议按下面顺序升级：

1. 把 `src/agent_tools.py` 里的固定工具包装成真正的 LangChain tools
2. 给每个工具补齐：
   - `@tool` 或 `StructuredTool`
   - 明确类型提示
   - 完整 docstring
3. 增加模型绑定层：
   - `model.bind_tools(tools)`
4. 在 LangGraph 中增加真正的工具执行节点：
   - `ToolNode`
5. 让模型自主决定：
   - 是否直接调用固定工具
   - 是否转向 SPARQL 生成

## 推荐升级后的链路

1. 用户提问
2. 模型判断是否可由固定工具直接回答
3. 若可回答：调用工具 -> 返回工具结果 -> 模型组织最终回答
4. 若不可回答：模型生成 SPARQL -> 执行 -> 模型根据结果回答
5. 若 SPARQL 失败：模型 fallback

## 为什么当前先不直接上 function calling

- 现在项目更需要“可跑、可展示、可答辩”的稳定版本
- 当前 OpenAI 模式已经能满足：
  - SPARQL 生成
  - 查询后回答
  - fallback
- 在此基础上再补 `@tool / bind_tools / ToolNode` 风险更低

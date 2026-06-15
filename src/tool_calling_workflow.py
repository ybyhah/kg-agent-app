from __future__ import annotations

import json
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from .langchain_tools import build_langchain_tools
from .models import QueryResult
from .openai_llm import OpenAIChatCompletionsClient
from .tools import QueryTools


class ToolCallingState(TypedDict, total=False):
    question: str
    messages: list[Any]
    tool_result: dict[str, Any] | None
    final_result: QueryResult | None
    route_after_tool: str


class ToolCallingWorkflow:
    def __init__(
        self,
        query_tools: QueryTools,
        llm_client: OpenAIChatCompletionsClient | None,
        answer_from_result,
        prepare_generated_execution,
        finalize_generated_execution,
        build_fallback_result,
        build_generated_plan,
    ):
        self.query_tools = query_tools
        self.llm_client = llm_client
        self.answer_from_result = answer_from_result
        self.prepare_generated_execution = prepare_generated_execution
        self.finalize_generated_execution = finalize_generated_execution
        self.build_fallback_result = build_fallback_result
        self.build_generated_plan = build_generated_plan
        self.tools = build_langchain_tools(query_tools)
        self.tool_node = ToolNode(self.tools, handle_tool_errors=True)
        self.available = self.llm_client is not None
        self.app = self._build_graph() if self.available else None

    def run(self, question: str) -> QueryResult | None:
        if not self.available or self.app is None:
            return None
        state = self.app.invoke({"question": question, "messages": [HumanMessage(content=question)]}, config={})
        return state.get("final_result")

    def _build_graph(self):
        graph = StateGraph(ToolCallingState)
        graph.add_node("llm_decide_tool", self._llm_decide_tool)
        graph.add_node("tools", self.tool_node)
        graph.add_node("after_tool", self._after_tool)
        graph.add_node("generate_sparql", self._generate_sparql)
        graph.add_node("fallback", self._fallback)

        graph.set_entry_point("llm_decide_tool")
        graph.add_conditional_edges(
            "llm_decide_tool",
            self._route_after_llm_decision,
            {
                "tools": "tools",
                "generated_sparql": "generate_sparql",
                "fallback": "fallback",
            },
        )
        graph.add_edge("tools", "after_tool")
        graph.add_conditional_edges(
            "after_tool",
            self._route_after_tool,
            {
                "done": END,
                "generated_sparql": "generate_sparql",
                "fallback": "fallback",
            },
        )
        graph.add_edge("generate_sparql", END)
        graph.add_edge("fallback", END)
        return graph.compile()

    def _llm_decide_tool(self, state: ToolCallingState) -> ToolCallingState:
        question = state.get("question", "").strip()
        if not question or self.llm_client is None:
            return {"route_after_tool": "fallback"}

        system_prompt = (
            "你是《印人传》知识图谱问答系统的问句解析节点。"
            " 你必须优先判断这个问题能否通过固定工具直接回答。"
            " 如果能，请调用最合适的一个工具；如果不能，请不要调用工具，而是直接回复 NO_TOOL。"
            " 只有在确实无法用固定工具回答时，才允许不调用工具。"
        )
        result = self.llm_client.bind_tools(self.tools, question, system_prompt=system_prompt)
        return {"messages": state.get("messages", []) + [result.message]}

    def _route_after_llm_decision(self, state: ToolCallingState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return "fallback"
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", []) or []
        if tool_calls:
            return "tools"
        return "generated_sparql"

    def _after_tool(self, state: ToolCallingState) -> ToolCallingState:
        messages = state.get("messages", [])
        tool_message = next((msg for msg in reversed(messages) if isinstance(msg, ToolMessage)), None)
        question = state.get("question", "")
        if tool_message is None:
            return {"route_after_tool": "generated_sparql"}

        try:
            parsed = json.loads(tool_message.content)
        except json.JSONDecodeError:
            return {"route_after_tool": "generated_sparql"}

        rows = parsed.get("rows") or []
        sparql = parsed.get("sparql")
        note = parsed.get("note") or ""
        if not rows:
            return {"route_after_tool": "generated_sparql"}

        route_stage = "LLM 选工具 -> ToolNode 执行 -> ToolMessage 回模型 -> LLM 组织回答"
        notes = [note, "当前结果来自 function calling 固定工具链路。", route_stage]
        deterministic_answer = self._deterministic_answer_from_rows(parsed)
        answer = self.answer_from_result(
            question=question,
            deterministic_answer=deterministic_answer,
            sparql=sparql,
            rows=rows,
            notes=notes,
        )
        return {
            "route_after_tool": "done",
            "tool_result": parsed,
            "final_result": QueryResult(
                mode="tool",
                answer=answer,
                sparql=sparql,
                rows=rows,
                notes=notes,
                route_label="function calling + 固定工具",
                route_stage=route_stage,
            ),
        }

    def _route_after_tool(self, state: ToolCallingState) -> str:
        return state.get("route_after_tool", "generated_sparql")

    def _generate_sparql(self, state: ToolCallingState) -> ToolCallingState:
        question = state.get("question", "")
        plan = self.build_generated_plan(question)
        if plan is None:
            return {"final_result": self.build_fallback_result(question)}
        execution = self.prepare_generated_execution(plan)
        final_result = self.finalize_generated_execution(plan, execution)
        return {"final_result": final_result}

    def _fallback(self, state: ToolCallingState) -> ToolCallingState:
        question = state.get("question", "")
        return {"final_result": self.build_fallback_result(question)}

    def _deterministic_answer_from_rows(self, payload: dict[str, Any]) -> str:
        rows = payload.get("rows") or []
        if not rows:
            return "当前固定工具未返回有效结果。"
        first_row = rows[0]
        visible_items: list[str] = []
        for key, value in first_row.items():
            if value:
                visible_items.append(f"{key}={value}")
        if not visible_items:
            return "当前固定工具已命中，但结果字段为空。"
        return f"图谱工具查询结果包括：{'；'.join(visible_items[:6])}"

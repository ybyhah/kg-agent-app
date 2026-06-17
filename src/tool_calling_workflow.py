from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
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
            "你是《印人传》知识图谱问答系统的工具选择节点。\n"
            "你的任务是判断问题应该调用哪个工具，而不是直接回答问题。\n"
            "重要规则：\n"
            "1. 只要问题可以用工具回答，就必须选择一个最合适的工具，不能直接返回文字答案\n"
            "2. 简单的事实查询（人物是谁、字、号、生卒年、师承、师兄弟、亲属、交游、流派）都必须调用工具\n"
            "3. 如果问题同时涉及字和号，使用 get_courtesy_and_art_name 工具\n"
            "4. 如果问题涉及师兄弟、同门，使用 get_classmates 工具\n"
            "5. 只有在明确需要复杂推理、多步骤查询、或工具完全无法覆盖时，才允许不调用工具\n"
            "6. 对于吴门印派/吴门派按吴门处理；对于文徵明/文征明/征仲按文徵明处理\n"
        )
        result = self.llm_client.bind_tools(self.tools, question, system_prompt=system_prompt)
        message = result.message
        tool_calls = getattr(message, "tool_calls", []) or []
        if not tool_calls:
            repaired_message = self._repair_missing_tool_call(question)
            if repaired_message is not None:
                message = repaired_message
        return {"messages": state.get("messages", []) + [message]}

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
        return f"图谱工具查询结果包括：{'; '.join(visible_items[:6])}"

    def _repair_missing_tool_call(self, question: str) -> AIMessage | None:
        normalized = question.strip().rstrip("？?。.")
        if not normalized:
            return None

        direct_rules = [
            (["的字和号", "字和号", "字与号", "字号"], "get_courtesy_and_art_name"),
            (["的字", "字是什么"], "get_courtesy_name"),
            (["的号", "号是什么"], "get_art_name"),
            (["生卒年", "出生于", "卒于", "生于"], "get_birth_death"),
            (["师兄弟", "同门", "师兄", "师弟"], "get_classmates"),
            (["老师", "师承"], "get_teacher_relations"),
            (["父亲", "儿子", "亲属", "家人"], "get_family_relations"),
            (["朋友", "交游"], "get_social_relations"),
            (["所属流派", "属于哪个流派", "哪个流派", "哪一派"], "get_school_membership"),
            (["关系网络", "相关人物", "关联人物"], "get_related_people"),
        ]
        for keywords, tool_name in direct_rules:
            if any(keyword in normalized for keyword in keywords):
                person_name = self._extract_person_name(normalized, keywords)
                if person_name:
                    return self._build_tool_call_message(tool_name, {"person_name": person_name})

        if "开创" in normalized or "创立" in normalized:
            school_name = self._extract_school_name(normalized)
            return self._build_tool_call_message("get_school_founder", {"school_name": school_name})

        pair_match = re.match(r"^(.+?)[与和](.+?)是什么关系$", normalized)
        if pair_match:
            return self._build_tool_call_message(
                "get_pair_relations",
                {
                    "person_a": pair_match.group(1).strip(),
                    "person_b": pair_match.group(2).strip(),
                },
            )

        if "是谁" in normalized:
            person_name = self._extract_person_name(normalized, ["是谁"])
            if person_name:
                return self._build_tool_call_message("get_person_labels", {"person_name": person_name})

        return None

    def _extract_person_name(self, question: str, keywords: list[str]) -> str:
        person_name = question
        for keyword in keywords:
            if keyword in person_name:
                person_name = person_name.split(keyword, 1)[0].strip()
        for prefix in ["请问", "请查询", "帮我查", "帮忙查", "告诉我"]:
            person_name = person_name.removeprefix(prefix).strip()
        return person_name

    def _extract_school_name(self, question: str) -> str:
        cleaned = question
        for token in ["谁开创了", "谁创立了", "哪位开创了", "哪位创立了", "开创者是谁", "创立者是谁"]:
            cleaned = cleaned.replace(token, "")
        cleaned = cleaned.strip()
        return cleaned or "吴门印派"

    def _build_tool_call_message(self, tool_name: str, args: dict[str, str]) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": tool_name,
                    "args": args,
                    "id": f"repair_{tool_name}",
                    "type": "tool_call",
                }
            ],
        )

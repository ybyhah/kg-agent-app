from __future__ import annotations

from typing import Any, Callable, TypedDict

from .models import QueryResult

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    END = "__end__"
    StateGraph = None
    LANGGRAPH_AVAILABLE = False


class WorkflowState(TypedDict, total=False):
    question: str
    plan: Any
    execution: Any
    final_result: QueryResult


class LangGraphWorkflowSkeleton:
    def __init__(
        self,
        plan_question: Callable[[str], Any],
        execute_tool_plan: Callable[[Any], QueryResult],
        prepare_generated_plan: Callable[[Any], Any],
        finalize_generated_plan: Callable[[Any, Any], QueryResult],
        build_fallback_result: Callable[[str], QueryResult],
    ):
        self.plan_question = plan_question
        self.execute_tool_plan = execute_tool_plan
        self.prepare_generated_plan = prepare_generated_plan
        self.finalize_generated_plan = finalize_generated_plan
        self.build_fallback_result = build_fallback_result
        self.available = LANGGRAPH_AVAILABLE
        self.app = self._build_graph() if self.available else None

    def run(self, question: str) -> QueryResult | None:
        if not self.available or self.app is None:
            return None
        state = self.app.invoke({"question": question})
        return state.get("final_result")

    def _build_graph(self):
        graph = StateGraph(WorkflowState)
        graph.add_node("plan_question", self._plan_node)
        graph.add_node("call_tool", self._tool_node)
        graph.add_node("generate_sparql", self._generated_prepare_node)
        graph.add_node("answer_from_result", self._generated_finalize_node)
        graph.add_node("fallback", self._fallback_node)

        graph.set_entry_point("plan_question")
        graph.add_conditional_edges(
            "plan_question",
            self._route_after_plan,
            {
                "tool": "call_tool",
                "generated_sparql": "generate_sparql",
                "fallback": "fallback",
            },
        )
        graph.add_edge("call_tool", END)
        graph.add_edge("generate_sparql", "answer_from_result")
        graph.add_edge("answer_from_result", END)
        graph.add_edge("fallback", END)
        return graph.compile()

    def _plan_node(self, state: WorkflowState) -> WorkflowState:
        question = state.get("question", "")
        return {"plan": self.plan_question(question)}

    def _route_after_plan(self, state: WorkflowState) -> str:
        plan = state.get("plan")
        return getattr(plan, "route_type", "fallback")

    def _tool_node(self, state: WorkflowState) -> WorkflowState:
        plan = state.get("plan")
        return {"final_result": self.execute_tool_plan(plan)}

    def _generated_prepare_node(self, state: WorkflowState) -> WorkflowState:
        plan = state.get("plan")
        return {"execution": self.prepare_generated_plan(plan)}

    def _generated_finalize_node(self, state: WorkflowState) -> WorkflowState:
        plan = state.get("plan")
        execution = state.get("execution")
        return {"final_result": self.finalize_generated_plan(plan, execution)}

    def _fallback_node(self, state: WorkflowState) -> WorkflowState:
        question = state.get("question", "")
        return {"final_result": self.build_fallback_result(question)}

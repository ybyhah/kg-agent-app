from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage

from src.tool_calling_workflow import ToolCallingWorkflow
from src.tools import QueryTools
from src.workflow import QueryResult


class DummyGraphStore:
    def __init__(self, rows: list[dict[str, str]] | None = None):
        self.rows = rows or []

    def query(self, sparql: str):
        return list(self.rows)


class FakeBoundResult:
    def __init__(self, message: AIMessage):
        self.message = message
        self.raw_text = message.content


class FakeOpenAIToolClient:
    def __init__(self, message: AIMessage):
        self.message = message

    def bind_tools(self, tools, prompt: str, system_prompt: str = ""):
        return FakeBoundResult(self.message)


class ToolCallingWorkflowTests(unittest.TestCase):
    def test_tool_calling_path_returns_tool_result(self) -> None:
        graph_store = DummyGraphStore(rows=[{"courtesyName": "寿承"}])
        query_tools = QueryTools(graph_store)
        llm_client = FakeOpenAIToolClient(
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_courtesy_name",
                        "args": {"person_name": "文彭"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            )
        )

        workflow = ToolCallingWorkflow(
            query_tools=query_tools,
            llm_client=llm_client,
            answer_from_result=lambda **kwargs: kwargs["deterministic_answer"],
            prepare_generated_execution=lambda plan: None,
            finalize_generated_execution=lambda plan, execution: QueryResult(mode="generated_sparql", answer="x"),
            build_fallback_result=lambda question: QueryResult(mode="fallback", answer="fallback"),
            build_generated_plan=lambda question: None,
        )

        result = workflow.run("文彭的字是什么？")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.mode, "tool")
        self.assertIn("courtesyName", result.answer)
        self.assertEqual(result.rows[0]["courtesyName"], "寿承")

    def test_no_tool_call_falls_through_to_generated_sparql(self) -> None:
        graph_store = DummyGraphStore(rows=[{"person": "x"}])
        query_tools = QueryTools(graph_store)
        llm_client = FakeOpenAIToolClient(AIMessage(content="NO_TOOL", tool_calls=[]))

        workflow = ToolCallingWorkflow(
            query_tools=query_tools,
            llm_client=llm_client,
            answer_from_result=lambda **kwargs: kwargs["deterministic_answer"],
            prepare_generated_execution=lambda plan: "prepared",
            finalize_generated_execution=lambda plan, execution: QueryResult(mode="generated_sparql", answer="generated"),
            build_fallback_result=lambda question: QueryResult(mode="fallback", answer="fallback"),
            build_generated_plan=lambda question: object(),
        )

        result = workflow.run("复杂问题")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.mode, "generated_sparql")


if __name__ == "__main__":
    unittest.main()

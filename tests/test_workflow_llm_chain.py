from __future__ import annotations

import unittest

from src.llm_workflow_support import WorkflowLlmSupport
from src.tools import QueryTools
from src.workflow import QueryWorkflow


class DummyGraphStore:
    def __init__(self, rows: list[dict[str, str]] | None = None, should_fail: bool = False):
        self.rows = rows or []
        self.should_fail = should_fail
        self.last_sparql = ""

    def query(self, sparql: str):
        self.last_sparql = sparql
        if self.should_fail:
            raise RuntimeError("graph unavailable")
        return list(self.rows)


class FakePromptClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            return ""
        return self.responses.pop(0)


class WorkflowLlmChainTests(unittest.TestCase):
    def test_generated_sparql_execution_then_llm_answer(self) -> None:
        graph_store = DummyGraphStore(rows=[{"founderLabel": "文彭"}])
        tools = QueryTools(graph_store)
        llm = WorkflowLlmSupport(
            client=FakePromptClient(
                [
                    """```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?founderLabel WHERE { ?s rdfs:label ?founderLabel . }
```""",
                    "根据查询结果，吴门印派的开创者是文彭。",
                ]
            ),
            provider_name="fake",
        )
        workflow = QueryWorkflow(tools, llm_support=llm)

        result = workflow.answer_question("请给出某某印学传统的开创者及相关标签信息")

        self.assertEqual(result.mode, "generated_sparql")
        self.assertIn("文彭", result.answer)
        self.assertIn("SELECT", result.sparql or "")
        self.assertTrue(result.rows)

    def test_generated_sparql_failure_uses_llm_direct_answer(self) -> None:
        graph_store = DummyGraphStore(should_fail=True)
        tools = QueryTools(graph_store)
        llm = WorkflowLlmSupport(
            client=FakePromptClient(
                [
                    """```sparql
SELECT ?person WHERE { ?person ?p ?o }
```""",
                    "图谱结论：当前本地图谱未返回足够结果，暂时无法确认。",
                ]
            ),
            provider_name="fake",
        )
        workflow = QueryWorkflow(tools, llm_support=llm)

        result = workflow.answer_question("请查询一个复杂关系问题")

        self.assertEqual(result.mode, "fallback")
        self.assertIn("图谱结论：当前本地图谱未返回足够结果，暂时无法确认。", result.answer)
        self.assertIn("SELECT", result.sparql or "")

    def test_reference_section_only_when_enabled(self) -> None:
        graph_store = DummyGraphStore(should_fail=True)
        tools = QueryTools(graph_store)
        llm = WorkflowLlmSupport(
            client=FakePromptClient(
                [
                    """```sparql
SELECT ?person WHERE { ?person ?p ?o }
```""",
                    "图谱结论：当前本地图谱未返回足够结果，暂时无法确认。模型参考说明：以下内容来自大模型内部知识，仅供参考，不作为本地图谱查询结论。",
                ]
            ),
            provider_name="fake",
            reference_mode=True,
        )
        workflow = QueryWorkflow(tools, llm_support=llm)

        result = workflow.answer_question("请查询一个复杂关系问题")

        self.assertEqual(result.mode, "fallback")
        self.assertIn("模型参考说明", result.answer)

    def test_simple_question_stays_on_tool_chain(self) -> None:
        graph_store = DummyGraphStore(rows=[{"courtesyName": "寿承"}])
        tools = QueryTools(graph_store)
        llm = WorkflowLlmSupport(
            client=FakePromptClient(
                [
                    "NO_TOOL",
                    "图谱结论：当前本地图谱未返回足够结果，暂时无法确认。",
                ]
            ),
            provider_name="fake",
        )
        workflow = QueryWorkflow(tools, llm_support=llm)

        result = workflow.answer_question("文彭的字是什么？")

        self.assertIn(result.mode, {"generated_sparql", "fallback"})


if __name__ == "__main__":
    unittest.main()

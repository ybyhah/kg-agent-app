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
    def test_complex_combo_question_prefers_generated_route(self) -> None:
        graph_store = DummyGraphStore(rows=[{"courtesyName": "寿承", "artName": "三桥", "deathYear": "万历癸酉"}])
        tools = QueryTools(graph_store)
        workflow = QueryWorkflow(tools, llm_support=WorkflowLlmSupport())

        self.assertTrue(workflow._should_prefer_generated_route("请同时给出文彭的字、号与生卒信息。"))
        self.assertTrue(workflow._should_prefer_generated_route("吴门印派代表人物有哪些？"))
        self.assertTrue(workflow._should_prefer_generated_route("赵大晋与吴门印派的关系是什么？"))

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

    def test_school_representatives_question_uses_generated_sparql(self) -> None:
        graph_store = DummyGraphStore(rows=[{"personLabel": "文彭"}, {"personLabel": "何震"}])
        tools = QueryTools(graph_store)
        workflow = QueryWorkflow(tools, llm_support=WorkflowLlmSupport())

        result = workflow.answer_question("吴门印派代表人物有哪些？")

        self.assertEqual(result.mode, "generated_sparql")
        self.assertIn("SELECT", result.sparql or "")
        self.assertEqual(len(result.rows), 2)

    def test_tool_answer_for_pair_relations_is_deduplicated(self) -> None:
        graph_store = DummyGraphStore(
            rows=[
                {"sourceLabel": "文彭", "targetLabel": "文徵明", "relationLabel": "fatherOf", "direction": "正向"},
                {"sourceLabel": "文彭", "targetLabel": "文徵明", "relationLabel": "父子", "direction": "反向"},
            ]
        )
        tools = QueryTools(graph_store)
        workflow = QueryWorkflow(tools, llm_support=WorkflowLlmSupport())

        answer = workflow._answer_from_tool_result("get_pair_relations", "文彭||文徵明", tools.get_pair_relations("文彭", "文徵明"))

        self.assertEqual(answer, "文彭与文徵明的直接关系包括：父子。")

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

    def test_reference_section_is_stripped_when_reference_mode_disabled(self) -> None:
        graph_store = DummyGraphStore(should_fail=True)
        tools = QueryTools(graph_store)
        llm = WorkflowLlmSupport(
            client=FakePromptClient(
                [
                    "图谱结论：当前本地图谱未返回足够结果，暂时无法确认。模型参考说明：这是一段不应在关闭参考模式时出现的补充。",
                ]
            ),
            provider_name="fake",
            reference_mode=False,
        )
        workflow = QueryWorkflow(tools, llm_support=llm)

        result = workflow._build_fallback_result("比较文彭与丁敬的篆刻理论差异。")

        self.assertEqual(result.mode, "fallback")
        self.assertIn("图谱结论：当前本地图谱未返回足够结果，暂时无法确认。", result.answer)
        self.assertNotIn("模型参考说明", result.answer)

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

    def test_reference_mode_retries_for_reference_section_when_first_reply_is_too_cautious(self) -> None:
        graph_store = DummyGraphStore(should_fail=True)
        tools = QueryTools(graph_store)
        llm = WorkflowLlmSupport(
            client=FakePromptClient(
                [
                    "图谱结论：当前本地图谱未返回足够结果，暂时无法确认。",
                    "模型参考说明：从模型内部知识看，文彭更偏明代文人篆刻传统，丁敬更强调浙派气息与金石趣味。此段仅供参考，不作为本地图谱结论。",
                ]
            ),
            provider_name="fake",
            reference_mode=True,
        )
        workflow = QueryWorkflow(tools, llm_support=llm)

        result = workflow._build_fallback_result("比较文彭与丁敬的篆刻理论差异。")

        self.assertEqual(result.mode, "fallback")
        self.assertIn("图谱结论：当前本地图谱未返回足够结果，暂时无法确认。", result.answer)
        self.assertIn("模型参考说明", result.answer)

    def test_curated_reference_mode_answer_for_wen_peng_and_ding_jing(self) -> None:
        graph_store = DummyGraphStore(should_fail=True)
        tools = QueryTools(graph_store)
        llm = WorkflowLlmSupport(
            client=FakePromptClient(
                [
                    "图谱结论：当前本地图谱未返回足够结果，暂时无法确认。",
                ]
            ),
            provider_name="fake",
            reference_mode=True,
        )
        workflow = QueryWorkflow(tools, llm_support=llm)

        result = workflow._build_fallback_result("比较文彭与丁敬的篆刻理论差异。")

        self.assertEqual(result.mode, "fallback")
        self.assertIn("图谱结论：当前本地图谱未返回足够结果，暂时无法确认。", result.answer)
        self.assertIn("模型参考说明", result.answer)
        self.assertIn("取法", result.answer)
        self.assertIn("刀法", result.answer)
        self.assertIn("审美", result.answer)
        self.assertIn("定位", result.answer)
        self.assertIn("章法", result.answer)
        self.assertIn("文彭", result.answer)
        self.assertIn("丁敬", result.answer)

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

        self.assertEqual(result.mode, "tool")
        self.assertIn("寿承", result.answer)


if __name__ == "__main__":
    unittest.main()

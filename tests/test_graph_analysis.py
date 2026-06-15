from __future__ import annotations

import unittest

from src.graph_analysis import GraphAnalysisService
from src.workflow import QueryWorkflow
from src.tools import QueryTools


class StubGraphStore:
    def __init__(self, rows):
        self.rows = rows

    def query(self, sparql: str):
        return list(self.rows)


class WorkflowFallbackGraphStore:
    def query(self, sparql: str):
        return []


class GraphAnalysisTests(unittest.TestCase):
    def test_graph_analysis_returns_centrality_and_communities(self) -> None:
        rows = [
            {
                "sourceLabel": "文徵明",
                "targetLabel": "文彭",
                "relationType": "http://www.yinrenzhuan.org/ontology#fatherOf",
                "relationTypeLabel": "父子",
                "sourceClass": "http://www.yinrenzhuan.org/ontology#Person",
                "targetClass": "http://www.yinrenzhuan.org/ontology#Person",
            },
            {
                "sourceLabel": "文彭",
                "targetLabel": "何震",
                "relationType": "http://www.yinrenzhuan.org/ontology#hasTeacher",
                "relationTypeLabel": "师承",
                "sourceClass": "http://www.yinrenzhuan.org/ontology#Person",
                "targetClass": "http://www.yinrenzhuan.org/ontology#Person",
            },
            {
                "sourceLabel": "文彭",
                "targetLabel": "吴门",
                "relationType": "http://www.yinrenzhuan.org/ontology#belongsToSchool",
                "relationTypeLabel": "所属流派",
                "sourceClass": "http://www.yinrenzhuan.org/ontology#Person",
                "targetClass": "http://www.yinrenzhuan.org/ontology#School",
            },
            {
                "sourceLabel": "文彭",
                "targetLabel": "吴门",
                "relationType": "http://www.yinrenzhuan.org/ontology#foundsSchool",
                "relationTypeLabel": "开创",
                "sourceClass": "http://www.yinrenzhuan.org/ontology#Person",
                "targetClass": "http://www.yinrenzhuan.org/ontology#School",
            },
        ]
        service = GraphAnalysisService(StubGraphStore(rows))

        result = service.build_overview()

        self.assertIn("centrality", result)
        self.assertTrue(result["centrality"]["topDegree"])
        self.assertTrue(result["communities"])
        self.assertTrue(result["schoolEvolution"])

    def test_shortest_path_returns_steps(self) -> None:
        rows = [
            {
                "sourceLabel": "文徵明",
                "targetLabel": "文彭",
                "relationType": "http://www.yinrenzhuan.org/ontology#fatherOf",
                "relationTypeLabel": "父子",
                "sourceClass": "http://www.yinrenzhuan.org/ontology#Person",
                "targetClass": "http://www.yinrenzhuan.org/ontology#Person",
            },
            {
                "sourceLabel": "文彭",
                "targetLabel": "何震",
                "relationType": "http://www.yinrenzhuan.org/ontology#hasTeacher",
                "relationTypeLabel": "师承",
                "sourceClass": "http://www.yinrenzhuan.org/ontology#Person",
                "targetClass": "http://www.yinrenzhuan.org/ontology#Person",
            },
        ]
        service = GraphAnalysisService(StubGraphStore(rows))

        result = service.find_shortest_path("文徵明", "何震")

        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 2)
        self.assertEqual(result["nodes"], ["文徵明", "文彭", "何震"])

    def test_workflow_fallback_contains_route_metadata(self) -> None:
        workflow = QueryWorkflow(QueryTools(WorkflowFallbackGraphStore()))

        result = workflow.answer_question("复杂问题")

        self.assertEqual(result.mode, "fallback")
        self.assertTrue(result.route_label)
        self.assertTrue(result.route_stage)


if __name__ == "__main__":
    unittest.main()

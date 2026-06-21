from __future__ import annotations

import unittest

from src.tools import QueryTools
from src.workflow import QueryWorkflow


class DirectRouteGraphStore:
    def query(self, sparql: str):
        if "hasCourtesyName" in sparql and "hasArtName" in sparql:
            return [{"label": "文彭", "courtesyName": "寿承", "artName": "三桥"}]
        if "belongsToSchool" in sparql and "foundsSchool" in sparql:
            return [
                {"personLabel": "文彭", "role": "开创者"},
                {"personLabel": "何震", "role": "成员"},
            ]
        return []


class WorkflowDirectRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = QueryWorkflow(QueryTools(DirectRouteGraphStore()))

    def test_direct_person_attr_question_returns_tool_answer(self) -> None:
        result = self.workflow.answer_question("文彭的字和号是什么？")
        self.assertEqual(result.mode, "tool")
        self.assertIn("寿承", result.answer)
        self.assertIn("三桥", result.answer)

    def test_school_representatives_question_no_longer_uses_direct_tool_route(self) -> None:
        result = self.workflow.answer_question("吴门印派有哪些代表人物？")
        self.assertNotEqual(result.mode, "tool")


if __name__ == "__main__":
    unittest.main()

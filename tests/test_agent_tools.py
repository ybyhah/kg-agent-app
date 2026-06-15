from __future__ import annotations

import unittest
from pathlib import Path

from src.bootstrap import create_app
from src.tools import ToolResult


class FakeQueryTools:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get_courtesy_name(self, person_name: str) -> ToolResult:
        self.calls.append(("get_courtesy_name", person_name))
        return ToolResult(
            name="get_courtesy_name",
            sparql="SELECT ?courtesyName WHERE {}",
            rows=[{"courtesyName": "寿承"}],
            note="fake",
        )


class AgentToolTests(unittest.TestCase):
    def test_tool_catalog_contains_course_aligned_metadata(self) -> None:
        from src.agent_tools import build_tool_catalog

        catalog = build_tool_catalog()
        courtesy_tool = next(tool for tool in catalog if tool["name"] == "get_courtesy_name")

        self.assertEqual(courtesy_tool["display_name"], "查询人物字")
        self.assertTrue(courtesy_tool["description"])
        self.assertTrue(courtesy_tool["parameters"])
        self.assertEqual(courtesy_tool["parameters"][0]["name"], "person_name")
        self.assertTrue(courtesy_tool["return_fields"])
        self.assertIn("SELECT", courtesy_tool["sparql_template"])
        self.assertTrue(courtesy_tool["course_references"])
        self.assertTrue(
            any(ref["pdf"] == "2026新4.pdf" and ref["page"] >= 155 for ref in courtesy_tool["course_references"])
        )

    def test_agent_toolbox_invokes_wrapped_query_tool(self) -> None:
        from src.agent_tools import AgentToolbox

        fake_tools = FakeQueryTools()
        toolbox = AgentToolbox(fake_tools)
        result = toolbox.invoke("get_courtesy_name", person_name="文彭")

        self.assertEqual(fake_tools.calls, [("get_courtesy_name", "文彭")])
        self.assertEqual(result.rows[0]["courtesyName"], "寿承")

    def test_tools_api_returns_tool_catalog(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        app = create_app(base_dir)
        client = app.test_client()

        response = client.get("/api/tools")
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        assert payload is not None
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["tools"])
        courtesy_tool = next(tool for tool in payload["tools"] if tool["name"] == "get_courtesy_name")
        self.assertEqual(courtesy_tool["parameters"][0]["name"], "person_name")
        self.assertTrue(courtesy_tool["course_references"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path

from src.bootstrap import create_app
from src.web import build_ui_text


class FrontendRenderTests(unittest.TestCase):
    def test_index_page_renders_core_sections(self) -> None:
        app = create_app(Path(r"D:\cxdownload\kg agent\kg_agent_app"))
        client = app.test_client()

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("印人传知识图谱智能体", html)
        self.assertIn("overviewTab", html)
        self.assertIn("networkTab", html)
        self.assertIn("analysisTab", html)
        self.assertIn("toggleReferenceModeBtn", html)
        self.assertIn("overviewImmersiveLayer", html)
        self.assertIn("heroVerticalTexts", html)
        self.assertIn("networkGalleryStage", html)
        self.assertIn("networkSpatialHint", html)
        self.assertNotIn("????", html)

    def test_ui_examples_cover_tool_and_generated_routes(self) -> None:
        ui = build_ui_text()

        examples = ui["qa_examples"]

        self.assertEqual(len(examples), 3)
        self.assertEqual(examples[0]["question"], "文彭的字和号是什么？")
        self.assertEqual(examples[0]["route"], "tool")
        self.assertEqual(examples[1]["question"], "吴门印派代表人物有哪些？")
        self.assertEqual(examples[1]["route"], "generated_sparql")
        self.assertEqual(examples[2]["question"], "比较文彭与丁敬的篆刻理论差异。")
        self.assertEqual(examples[2]["route"], "fallback")
        self.assertTrue(all("question" in item and "description" in item for item in examples))


if __name__ == "__main__":
    unittest.main()

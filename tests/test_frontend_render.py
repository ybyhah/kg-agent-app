from __future__ import annotations

import unittest
from pathlib import Path

from src.bootstrap import create_app


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


if __name__ == "__main__":
    unittest.main()

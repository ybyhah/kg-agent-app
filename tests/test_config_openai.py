from __future__ import annotations

import os
import unittest
from pathlib import Path

from src.config import AppConfig


class ConfigOpenAITests(unittest.TestCase):
    def test_openai_config_fields_can_be_loaded_from_env(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        previous = {
            "KG_AGENT_LLM_MODE": os.environ.get("KG_AGENT_LLM_MODE"),
            "KG_AGENT_OPENAI_MODEL": os.environ.get("KG_AGENT_OPENAI_MODEL"),
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "KG_AGENT_LLM_REFERENCE_MODE": os.environ.get("KG_AGENT_LLM_REFERENCE_MODE"),
        }
        try:
            os.environ["KG_AGENT_LLM_MODE"] = "openai"
            os.environ["KG_AGENT_OPENAI_MODEL"] = "gpt-5.5"
            os.environ["OPENAI_API_KEY"] = "test-key"
            os.environ["KG_AGENT_LLM_REFERENCE_MODE"] = "1"
            config = AppConfig.from_base_dir(base_dir)
            self.assertEqual(config.llm_mode, "openai")
            self.assertEqual(config.llm_model_name, "gpt-5.5")
            self.assertEqual(config.openai_api_key, "test-key")
            self.assertTrue(config.llm_reference_mode)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.config import AppConfig


class ConfigOpenAITests(unittest.TestCase):
    def test_openai_compatible_config_fields_can_be_loaded_from_env(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        previous = {
            "KG_AGENT_LLM_MODE": os.environ.get("KG_AGENT_LLM_MODE"),
            "KG_AGENT_OPENAI_MODEL": os.environ.get("KG_AGENT_OPENAI_MODEL"),
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
            "KG_AGENT_OPENAI_BASE_URL": os.environ.get("KG_AGENT_OPENAI_BASE_URL"),
            "KG_AGENT_LLM_REFERENCE_MODE": os.environ.get("KG_AGENT_LLM_REFERENCE_MODE"),
        }
        try:
            os.environ["KG_AGENT_LLM_MODE"] = "openai"
            os.environ["KG_AGENT_OPENAI_MODEL"] = "deepseek-v4-flash"
            os.environ["OPENAI_API_KEY"] = ""
            os.environ["DEEPSEEK_API_KEY"] = "test-deepseek-key"
            os.environ["KG_AGENT_OPENAI_BASE_URL"] = "https://api.deepseek.com"
            os.environ["KG_AGENT_LLM_REFERENCE_MODE"] = "1"
            config = AppConfig.from_base_dir(base_dir)
            self.assertEqual(config.llm_mode, "openai")
            self.assertEqual(config.llm_model_name, "deepseek-v4-flash")
            self.assertEqual(config.openai_api_key, "test-deepseek-key")
            self.assertEqual(config.openai_base_url, "https://api.deepseek.com")
            self.assertTrue(config.llm_reference_mode)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_deepseek_defaults_are_applied_when_not_overridden(self) -> None:
        previous = {
            "KG_AGENT_OPENAI_MODEL": os.environ.get("KG_AGENT_OPENAI_MODEL"),
            "KG_AGENT_OPENAI_BASE_URL": os.environ.get("KG_AGENT_OPENAI_BASE_URL"),
            "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL"),
        }
        try:
            os.environ.pop("KG_AGENT_OPENAI_MODEL", None)
            os.environ.pop("KG_AGENT_OPENAI_BASE_URL", None)
            os.environ.pop("OPENAI_BASE_URL", None)
            with tempfile.TemporaryDirectory() as temp_dir:
                config = AppConfig.from_base_dir(Path(temp_dir))
                self.assertEqual(config.llm_model_name, "deepseek-v4-flash")
                self.assertEqual(config.openai_base_url, "https://api.deepseek.com")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()

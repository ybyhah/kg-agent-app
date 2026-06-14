from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kg_agent_app.src.information_extraction import (
    JsonExtractionParser,
    PersonRecordExtractor,
    extract_records_to_file,
    load_person_records,
)


class StubClient:
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._responses:
            raise AssertionError("No more stub responses configured.")
        return self._responses.pop(0)


class InformationExtractionTests(unittest.TestCase):
    def test_load_person_records_reads_utf8_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "records.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "record_id": "YRZ_TEST_1",
                            "person_name": "方仲芝",
                            "source_text": "方仲芝，以其工象牙黄杨也。",
                            "text_length": 13,
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            records = load_person_records(input_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].person_name, "方仲芝")
        self.assertEqual(records[0].record_id, "YRZ_TEST_1")

    def test_json_extraction_parser_accepts_markdown_fence(self) -> None:
        raw_response = """```json
        {
          "entities": [{"name": "方仲芝", "category": "PERSON", "evidence": "方仲芝"}],
          "attributes": [{"subject": "方仲芝", "attribute": "技艺", "value": "工象牙黄杨", "evidence": "工象牙黄杨"}],
          "relations": []
        }
        ```"""

        payload = JsonExtractionParser().parse(raw_response)

        self.assertEqual(payload.entities[0].name, "方仲芝")
        self.assertEqual(payload.attributes[0].attribute, "技艺")
        self.assertEqual(payload.attributes[0].value, "工象牙黄杨")

    def test_extract_records_to_file_writes_structured_results(self) -> None:
        stub_client = StubClient(
            [
                json.dumps(
                    {
                        "entities": [
                            {
                                "name": "方仲芝",
                                "category": "PERSON",
                                "evidence": "方仲芝",
                            }
                        ],
                        "attributes": [
                            {
                                "subject": "方仲芝",
                                "attribute": "技艺",
                                "value": "工象牙黄杨",
                                "evidence": "工象牙黄杨",
                            }
                        ],
                        "relations": [
                            {
                                "source": "方仲芝",
                                "relation": "出现在",
                                "target": "印人传合集",
                                "evidence": "印人传合集",
                            }
                        ],
                    },
                    ensure_ascii=False,
                )
            ]
        )
        extractor = PersonRecordExtractor(client=stub_client)

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "records.json"
            output_path = Path(tmp_dir) / "results.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "record_id": "YRZ_TEST_1",
                            "person_name": "方仲芝",
                            "source_text": "方仲芝，以其工象牙黄杨也。印人传合集。",
                            "text_length": 18,
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            results = extract_records_to_file(
                input_path=input_path,
                output_path=output_path,
                extractor=extractor,
                limit=1,
            )

            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(results), 1)
        self.assertEqual(written[0]["record_id"], "YRZ_TEST_1")
        self.assertEqual(written[0]["entities"][0]["name"], "方仲芝")
        self.assertEqual(written[0]["attributes"][0]["attribute"], "技艺")
        self.assertEqual(written[0]["relations"][0]["target"], "印人传合集")
        self.assertEqual(len(stub_client.prompts), 1)


if __name__ == "__main__":
    unittest.main()

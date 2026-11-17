"""Smoke tests for the repository foundation; no third-party packages required."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FoundationTests(unittest.TestCase):
    def test_project_schema_is_valid_json_and_has_expected_contract(self):
        schema = json.loads((ROOT / "schemas/project.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["type"], "object")
        self.assertIn("project_id", schema["required"])
        self.assertIn("status", schema["properties"])

    def test_workflow_schema_is_valid_json_and_has_explicit_states(self):
        schema = json.loads((ROOT / "schemas/workflow_state.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["type"], "object")
        self.assertIn("current_stage", schema["required"])
        self.assertIn("waiting_for_human", schema["properties"]["status"]["enum"])
        self.assertIn("blocked", schema["properties"]["status"]["enum"])

    def test_package_version_is_importable(self):
        import ai_yas

        self.assertEqual(ai_yas.__version__, "0.2.0")


if __name__ == "__main__":
    unittest.main()

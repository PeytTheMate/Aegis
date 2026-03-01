from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.mcv.service import compile_file, diff_files


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"


class TestCompileAndDiff(unittest.TestCase):
    def test_compile_creates_hashed_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "compiled.json"
            validation, artifact = compile_file(CONFIG_ROOT / "valid_mission.yaml", out)
            self.assertTrue(validation.valid)
            self.assertIsNotNone(artifact)

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("schema_hash", payload)
            self.assertIn("config_hash", payload)
            self.assertEqual(payload["artifact_version"], 1)

    def test_semantic_diff_ignores_unit_representation(self) -> None:
        result_a, result_b, diff = diff_files(
            CONFIG_ROOT / "valid_mission.yaml",
            CONFIG_ROOT / "semantic_same_units.yaml",
        )
        self.assertTrue(result_a.valid)
        self.assertTrue(result_b.valid)
        self.assertEqual(diff, [])


if __name__ == "__main__":
    unittest.main()

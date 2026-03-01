from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.mcv.service import compile_file
from src.pbt.runner import run_property_tests


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"


class TestPipeline(unittest.TestCase):
    def test_compile_then_pbt_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            compiled_path = Path(tmp) / "compiled.json"
            validation, artifact = compile_file(CONFIG_ROOT / "valid_mission.yaml", compiled_path)
            self.assertTrue(validation.valid)
            self.assertTrue(compiled_path.exists())
            self.assertIsNotNone(artifact)

            summary = run_property_tests(
                compiled_artifact=artifact.artifact,
                runs=5,
                profile="nominal",
                failure_root=Path(tmp) / "failures",
                base_seed=10,
            )
            self.assertEqual(summary["runs"], 5)


if __name__ == "__main__":
    unittest.main()

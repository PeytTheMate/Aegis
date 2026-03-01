from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.mcv.service import compile_file
from src.pbt.runner import replay_bundle, run_property_tests, shrink_bundle


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"


class TestRunnerBundleAndShrink(unittest.TestCase):
    def test_failure_bundle_and_replay(self) -> None:
        validation, artifact = compile_file(CONFIG_ROOT / "valid_tight_aoa.yaml")
        self.assertTrue(validation.valid)
        self.assertIsNotNone(artifact)

        with tempfile.TemporaryDirectory() as tmp:
            summary = run_property_tests(
                compiled_artifact=artifact.artifact,
                runs=20,
                profile="degraded",
                failure_root=tmp,
                base_seed=1337,
            )
            self.assertGreater(summary["failure_count"], 0)
            bundle = summary["failures"][0]

            replay = replay_bundle(bundle)
            self.assertFalse(replay["passed"])

            shrink = shrink_bundle(bundle)
            self.assertGreater(len(shrink["violations"]), 0)
            self.assertTrue((Path(bundle) / "scenario_shrunk.json").exists())


if __name__ == "__main__":
    unittest.main()

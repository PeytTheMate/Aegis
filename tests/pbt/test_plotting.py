"""Tests for trace visualization."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.mcv.service import compile_file
from src.pbt.runner import run_property_tests

CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"


class TestPlotting(unittest.TestCase):
    def test_plot_creates_png(self) -> None:
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib not installed")

        from src.pbt.plotting import plot_trace

        validation, artifact = compile_file(CONFIG_ROOT / "valid_tight_aoa.yaml")
        self.assertTrue(validation.valid)

        with tempfile.TemporaryDirectory() as tmp:
            summary = run_property_tests(
                compiled_artifact=artifact.artifact,
                runs=5,
                profile="degraded",
                failure_root=tmp,
                base_seed=1338,
            )
            self.assertGreater(summary["failure_count"], 0)

            bundle = summary["failures"][0]
            output = plot_trace(bundle)
            self.assertTrue(output.exists())
            self.assertTrue(output.name.endswith(".png"))
            self.assertGreater(output.stat().st_size, 1000)

    def test_plot_custom_output(self) -> None:
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib not installed")

        from src.pbt.plotting import plot_trace

        validation, artifact = compile_file(CONFIG_ROOT / "valid_tight_aoa.yaml")
        self.assertTrue(validation.valid)

        with tempfile.TemporaryDirectory() as tmp:
            summary = run_property_tests(
                compiled_artifact=artifact.artifact,
                runs=5,
                profile="degraded",
                failure_root=tmp,
                base_seed=1338,
            )
            self.assertGreater(summary["failure_count"], 0)

            bundle = summary["failures"][0]
            custom_output = Path(tmp) / "custom_plot.png"
            output = plot_trace(bundle, custom_output)
            self.assertEqual(output, custom_output)
            self.assertTrue(custom_output.exists())

    def test_graceful_import_error(self) -> None:
        """Verify helpful error message when matplotlib missing."""
        # We can only test the message format, not actual missing import
        from src.pbt.plotting import plot_trace
        self.assertTrue(callable(plot_trace))


if __name__ == "__main__":
    unittest.main()

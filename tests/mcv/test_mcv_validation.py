from __future__ import annotations

import math
import unittest
from pathlib import Path

from src.mcv.service import validate_file


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"


class TestMCVValidation(unittest.TestCase):
    def test_valid_config_normalizes_units(self) -> None:
        result = validate_file(CONFIG_ROOT / "valid_mission.yaml")
        self.assertTrue(result.valid)

        normalized = result.normalized_config
        self.assertAlmostEqual(normalized["guidance"]["max_angle_of_attack"], math.radians(12), places=6)
        self.assertAlmostEqual(normalized["navigation"]["imu"]["max_latency"], 0.02, places=6)
        self.assertAlmostEqual(normalized["control"]["actuator"]["max_gimbal_rate"], math.radians(8), places=6)

    def test_defaults_injected_deterministically(self) -> None:
        minimal_path = CONFIG_ROOT / "minimal_defaults.yaml"
        minimal_path.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "vehicle: falcon_like",
                    'mission_id: "MIN-1"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        try:
            result = validate_file(minimal_path)
            self.assertTrue(result.valid)
            self.assertEqual(result.normalized_config["navigation"]["imu"]["enabled"], True)
            self.assertEqual(result.normalized_config["control"]["mode_logic"]["abort_requires"], ["imu"])
        finally:
            minimal_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

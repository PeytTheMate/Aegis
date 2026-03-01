"""Tests for 3-DoF trajectory simulator."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.mcv.service import compile_file
from src.pbt.generator import generate_scenario
from src.pbt.sut import SimulationResult, run_scenario

CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"

# Minimal compiled config for direct use in tests
_MINIMAL_CONFIG: dict = {
    "canonical_config": {
        "guidance": {"enabled": True, "max_angle_of_attack": 0.2094, "max_q": 65000.0},
        "navigation": {
            "imu": {"enabled": True, "max_latency": 0.02},
            "gps": {"enabled": True, "max_latency": 0.25},
        },
        "control": {
            "actuator": {"max_gimbal_rate": 0.1396, "max_gimbal_angle": 0.2618},
            "mode_logic": {"allow_autonomous_abort": False, "abort_requires": ["imu"]},
        },
        "comms": {"packet_loss_budget": 0.02, "time_sync": {"max_skew": 0.005}},
    }
}

ORIGINAL_TRACE_KEYS = {
    "time_s", "mode", "aoa_rad", "max_aoa_rad", "command_rad",
    "packet_loss", "abort_requested", "abort_requested_at", "is_finite",
}

NEW_3DOF_KEYS = {
    "altitude_m", "velocity_m_s", "acceleration_g", "dynamic_pressure_Pa",
    "mach", "thrust_N", "mass_kg", "pitch_rad", "flight_path_angle_rad",
}


class TestSut3DoF(unittest.TestCase):
    def _run_nominal(self, duration: float = 30.0) -> SimulationResult:
        scenario = {"seed": 42, "profile": "nominal", "duration_s": duration, "faults": []}
        return run_scenario(_MINIMAL_CONFIG, scenario)

    def test_backward_compatible_trace_keys(self) -> None:
        result = self._run_nominal()
        row = result.trace[0]
        for key in ORIGINAL_TRACE_KEYS:
            self.assertIn(key, row, f"Missing original trace key: {key}")

    def test_trace_has_3dof_fields(self) -> None:
        result = self._run_nominal()
        row = result.trace[0]
        for key in NEW_3DOF_KEYS:
            self.assertIn(key, row, f"Missing 3-DoF trace key: {key}")

    def test_altitude_increases_during_ascent(self) -> None:
        result = self._run_nominal(duration=20.0)
        altitudes = [row["altitude_m"] for row in result.trace]
        # After initial few steps, altitude should generally increase
        mid = len(altitudes) // 2
        self.assertGreater(altitudes[-1], altitudes[mid],
                           "Altitude should increase during powered ascent")

    def test_mass_decreases_during_burn(self) -> None:
        result = self._run_nominal(duration=20.0)
        masses = [row["mass_kg"] for row in result.trace]
        self.assertLess(masses[-1], masses[0],
                        "Mass should decrease due to fuel consumption")

    def test_determinism(self) -> None:
        scenario = {"seed": 1337, "profile": "nominal", "duration_s": 10.0, "faults": []}
        a = run_scenario(_MINIMAL_CONFIG, scenario)
        b = run_scenario(_MINIMAL_CONFIG, scenario)
        self.assertEqual(len(a.trace), len(b.trace))
        for ra, rb in zip(a.trace, b.trace):
            self.assertEqual(ra["aoa_rad"], rb["aoa_rad"])
            self.assertEqual(ra["altitude_m"], rb["altitude_m"])

    def test_dynamic_pressure_positive_in_atmosphere(self) -> None:
        result = self._run_nominal(duration=10.0)
        # After a few steps the vehicle is moving, dynamic pressure should be > 0
        late_rows = result.trace[5:]
        for row in late_rows:
            self.assertGreater(row["dynamic_pressure_Pa"], 0.0)

    def test_mach_increases_during_ascent(self) -> None:
        result = self._run_nominal(duration=30.0)
        early_mach = result.trace[10]["mach"]
        late_mach = result.trace[-1]["mach"]
        self.assertGreater(late_mach, early_mach,
                           "Mach number should increase as vehicle accelerates")

    def test_abort_mode_reachable(self) -> None:
        """With mode_churn fault, abort should be triggered."""
        scenario = {
            "seed": 99,
            "profile": "degraded",
            "duration_s": 20.0,
            "faults": [{"type": "mode_churn", "start": 1.0, "end": 15.0, "period_s": 0.5}],
        }
        result = run_scenario(_MINIMAL_CONFIG, scenario)
        modes = {row["mode"] for row in result.trace}
        self.assertIn("ABORT", modes, "Abort should be reachable via mode_churn fault")

    def test_all_outputs_finite(self) -> None:
        result = self._run_nominal(duration=30.0)
        for row in result.trace:
            self.assertTrue(row["is_finite"], f"Non-finite output at t={row['time_s']}")

    def test_compiled_config_from_file(self) -> None:
        """Verify simulator works with a real compiled config."""
        validation, artifact = compile_file(CONFIG_ROOT / "valid_mission.yaml")
        self.assertTrue(validation.valid)
        scenario = generate_scenario(seed=42, profile="nominal")
        result = run_scenario(artifact.artifact, scenario)
        self.assertGreater(len(result.trace), 0)


if __name__ == "__main__":
    unittest.main()

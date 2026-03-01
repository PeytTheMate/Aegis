"""Tests for Kalman filter module and PBT-005 integration."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.pbt.kalman import (
    EKF,
    create_default_ekf,
    mat_identity,
    mat_inv,
    mat_mul,
    mat_zeros,
)
from src.pbt.generator import generate_scenario
from src.pbt.properties import evaluate_properties
from src.pbt.sut import run_scenario

CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"

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


class TestMatrixOps(unittest.TestCase):
    def test_identity_inverse(self) -> None:
        I = mat_identity(3)
        I_inv = mat_inv(I)
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                self.assertAlmostEqual(I_inv[i][j], expected, places=10)

    def test_known_inverse(self) -> None:
        # [[2, 1], [5, 3]] has inverse [[3, -1], [-5, 2]]
        A = [[2.0, 1.0], [5.0, 3.0]]
        A_inv = mat_inv(A)
        self.assertAlmostEqual(A_inv[0][0], 3.0, places=10)
        self.assertAlmostEqual(A_inv[0][1], -1.0, places=10)
        self.assertAlmostEqual(A_inv[1][0], -5.0, places=10)
        self.assertAlmostEqual(A_inv[1][1], 2.0, places=10)

    def test_inverse_roundtrip(self) -> None:
        A = [[1.0, 2.0, 3.0], [0.0, 1.0, 4.0], [5.0, 6.0, 0.0]]
        A_inv = mat_inv(A)
        product = mat_mul(A, A_inv)
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                self.assertAlmostEqual(product[i][j], expected, places=8)


class TestKalmanFilter(unittest.TestCase):
    def test_kf_creation(self) -> None:
        kf = create_default_ekf()
        self.assertEqual(len(kf.x_hat), 5)
        self.assertEqual(len(kf.P), 5)

    def test_kf_converges_no_noise(self) -> None:
        """With perfect measurements, estimate should match state."""
        kf = create_default_ekf([0.0, 0.0, 10.0, 20.0, 0.05])
        # Feed perfect measurements for 50 steps
        true_x, true_y = 0.0, 0.0
        true_vx, true_vy = 10.0, 20.0
        true_aoa = 0.05
        dt = 0.1
        for _ in range(50):
            true_x += true_vx * dt
            true_y += true_vy * dt
            kf.predict(0.0, 0.0, 0.0, dt)
            kf.update_imu(true_vx, true_vy, true_aoa)
            kf.update_gps(true_x, true_y)

        self.assertAlmostEqual(kf.x_hat[0], true_x, places=0)
        self.assertAlmostEqual(kf.x_hat[1], true_y, places=0)
        self.assertAlmostEqual(kf.x_hat[4], true_aoa, places=2)

    def test_kf_tracks_linear_motion(self) -> None:
        """KF should track constant-velocity motion within reasonable bounds."""
        kf = create_default_ekf([0.0, 0.0, 5.0, 10.0, 0.0])
        dt = 0.1
        import random
        rng = random.Random(42)
        for step in range(100):
            true_x = 5.0 * step * dt
            true_y = 10.0 * step * dt
            kf.predict(0.0, 0.0, 0.0, dt)
            kf.update_imu(5.0 + rng.gauss(0, 0.1), 10.0 + rng.gauss(0, 0.1), 0.0)
            if step % 10 == 0:
                kf.update_gps(true_x + rng.gauss(0, 1.0), true_y + rng.gauss(0, 1.0))

        # Velocity estimates should be close
        self.assertAlmostEqual(kf.x_hat[2], 5.0, delta=1.0)
        self.assertAlmostEqual(kf.x_hat[3], 10.0, delta=1.0)

    def test_imu_bias_increases_innovation(self) -> None:
        """With IMU bias, KF innovation should be larger than without."""
        dt = 0.1
        # Run without bias
        kf_clean = create_default_ekf()
        for _ in range(20):
            kf_clean.predict(0.0, 0.0, 0.0, dt)
            kf_clean.update_imu(0.0, 0.1, 0.0)
        innovation_clean = sum(abs(v) for v in kf_clean.innovation)

        # Run with bias
        kf_biased = create_default_ekf()
        for _ in range(20):
            kf_biased.predict(0.0, 0.0, 0.0, dt)
            kf_biased.update_imu(5.0, 5.0, 0.5)  # large bias
        innovation_biased = sum(abs(v) for v in kf_biased.innovation)

        self.assertGreater(innovation_biased, innovation_clean)

    def test_estimation_error_bounded_nominal(self) -> None:
        """Run a full nominal scenario, check PBT-005 passes."""
        scenario = {"seed": 42, "profile": "nominal", "duration_s": 30.0, "faults": []}
        result = run_scenario(_MINIMAL_CONFIG, scenario)
        config = _MINIMAL_CONFIG["canonical_config"]
        violations = evaluate_properties(result.trace, config)
        pbt005 = [v for v in violations if v["property_id"] == "PBT-005"]
        self.assertEqual(len(pbt005), 0, "PBT-005 should pass under nominal conditions")

    def test_kf_fields_in_trace(self) -> None:
        """Verify KF trace fields are present."""
        scenario = {"seed": 1, "profile": "nominal", "duration_s": 5.0, "faults": []}
        result = run_scenario(_MINIMAL_CONFIG, scenario)
        row = result.trace[0]
        self.assertIn("estimated_aoa_rad", row)
        self.assertIn("estimation_error_rad", row)
        self.assertIn("kf_innovation", row)


if __name__ == "__main__":
    unittest.main()

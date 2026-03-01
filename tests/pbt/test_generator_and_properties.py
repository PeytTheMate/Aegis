from __future__ import annotations

import unittest

from src.pbt.generator import generate_scenario


class TestGeneratorAndProperties(unittest.TestCase):
    def test_scenario_generation_is_deterministic(self) -> None:
        a = generate_scenario(1337, profile="degraded")
        b = generate_scenario(1337, profile="degraded")
        self.assertEqual(a, b)

    def test_scenario_structure(self) -> None:
        scenario = generate_scenario(7, profile="nominal")
        self.assertIn("seed", scenario)
        self.assertIn("duration_s", scenario)
        self.assertIsInstance(scenario["faults"], list)


if __name__ == "__main__":
    unittest.main()

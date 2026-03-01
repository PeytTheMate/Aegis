from __future__ import annotations

import unittest

from src.assurance.formal_mode_logic import verify_mode_logic


class TestFormalModeLogic(unittest.TestCase):
    def test_formal_checker_passes_default_model(self) -> None:
        report = verify_mode_logic()
        self.assertTrue(report["passed"])
        for item in report["properties"]:
            self.assertTrue(item["passed"])

    def test_formal_checker_detects_abort_exit_bug(self) -> None:
        report = verify_mode_logic(allow_abort_exit=True)
        self.assertFalse(report["passed"])
        result_by_id = {item["property_id"]: item for item in report["properties"]}
        self.assertFalse(result_by_id["FML-002"]["passed"])
        self.assertIsNotNone(result_by_id["FML-002"]["counterexample"])


if __name__ == "__main__":
    unittest.main()

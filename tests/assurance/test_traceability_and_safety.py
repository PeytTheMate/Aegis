from __future__ import annotations

import unittest

from src.assurance.safety_case import build_safety_report
from src.assurance.traceability import build_traceability_report


class TestTraceabilityAndSafety(unittest.TestCase):
    def test_traceability_report_passes(self) -> None:
        report = build_traceability_report()
        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["summary"]["requirements_total"], 8)
        self.assertEqual(report["summary"]["issues_total"], 0)

    def test_safety_case_report_passes(self) -> None:
        report = build_safety_report()
        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["summary"]["hazards_total"], 4)
        self.assertEqual(report["summary"]["issues_total"], 0)


if __name__ == "__main__":
    unittest.main()

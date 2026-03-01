from __future__ import annotations

import unittest
from pathlib import Path

from src.mcv.service import validate_file


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"


class TestMCVConstraints(unittest.TestCase):
    def test_invalid_autonomous_abort(self) -> None:
        result = validate_file(CONFIG_ROOT / "invalid_autonomous_abort.yaml")
        self.assertFalse(result.valid)
        ids = {diagnostic.rule_id for diagnostic in result.diagnostics}
        self.assertIn("MCV-016", ids)
        self.assertIn("MCV-017", ids)

    def test_unknown_field_is_reported(self) -> None:
        path = CONFIG_ROOT / "invalid_unknown_field.yaml"
        path.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "vehicle: falcon_like",
                    "mission_id: UNKNOWN-1",
                    "guidance:",
                    "  enabled: true",
                    '  max_angle_of_attack: "12 deg"',
                    '  max_q: "65000 Pa"',
                    "  mystery_field: 42",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        try:
            result = validate_file(path)
            self.assertFalse(result.valid)
            ids = {diagnostic.rule_id for diagnostic in result.diagnostics}
            self.assertIn("MCV-000", ids)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


class TestAssuranceCLI(unittest.TestCase):
    def test_assurance_check_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "assurance_reports"
            proc = subprocess.run(
                [
                    "python3",
                    "-m",
                    "src.cli",
                    "assurance",
                    "check",
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)
            self.assertTrue((output_dir / "traceability_report.json").exists())
            self.assertTrue((output_dir / "safety_report.json").exists())
            self.assertTrue((output_dir / "formal_report.json").exists())


if __name__ == "__main__":
    unittest.main()

"""Failure bundle creation and loading."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.io_utils import read_text, write_json



def _bundle_dir(root: str | Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    suffix = datetime.now(UTC).strftime("%f")[:6]
    path = Path(root) / f"{timestamp}_{suffix}"
    path.mkdir(parents=True, exist_ok=False)
    return path



def write_failure_bundle(root: str | Path, compiled_artifact: dict[str, Any], scenario: dict[str, Any], trace: list[dict[str, Any]], violations: list[dict[str, Any]]) -> Path:
    bundle_path = _bundle_dir(root)

    write_json(bundle_path / "compiled_config.json", compiled_artifact)
    write_json(bundle_path / "scenario.json", scenario)

    with (bundle_path / "trace.csv").open("w", newline="", encoding="utf-8") as handle:
        if trace:
            writer = csv.DictWriter(handle, fieldnames=list(trace[0].keys()))
            writer.writeheader()
            writer.writerows(trace)

    report_lines = [
        "# Failure Report",
        "",
        f"- Created: {datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')}",
        f"- Seed: {scenario.get('seed')}",
        f"- Profile: {scenario.get('profile')}",
        "",
        "## Violations",
    ]
    for violation in violations:
        report_lines.append(f"- {violation['property_id']}: {violation['message']} @ t={violation.get('time_s')}")

    (bundle_path / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    repro = "#!/usr/bin/env bash\npython3 -m src.cli pbt replay \"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
    repro_path = bundle_path / "repro.sh"
    repro_path.write_text(repro, encoding="utf-8")
    repro_path.chmod(0o755)

    return bundle_path



def load_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    root = Path(bundle_dir)
    compiled = json.loads(read_text(root / "compiled_config.json"))
    scenario = json.loads(read_text(root / "scenario.json"))
    return {
        "root": str(root),
        "compiled": compiled,
        "scenario": scenario,
    }

"""Hazard log and safety-case consistency validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.assurance.catalog import collect_constraint_ids, collect_property_ids, load_yaml_mapping, repo_root
from src.assurance.formal_ids import FORMAL_PROPERTY_IDS



def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("Expected list[str].")



def build_safety_report(
    requirements_path: str | Path | None = None,
    hazard_log_path: str | Path | None = None,
    safety_case_path: str | Path | None = None,
) -> dict[str, Any]:
    root = repo_root()

    req_path = Path(requirements_path) if requirements_path else root / "assurance" / "requirements.yaml"
    hazard_path = Path(hazard_log_path) if hazard_log_path else root / "assurance" / "hazard_log.yaml"
    case_path = Path(safety_case_path) if safety_case_path else root / "assurance" / "safety_case.yaml"

    req_data = load_yaml_mapping(req_path)
    hazard_data = load_yaml_mapping(hazard_path)
    case_data = load_yaml_mapping(case_path)

    requirements = req_data.get("requirements")
    hazards = hazard_data.get("hazards")
    claims = case_data.get("claims")
    if not isinstance(requirements, dict):
        raise ValueError("requirements.yaml missing requirements mapping")
    if not isinstance(hazards, dict):
        raise ValueError("hazard_log.yaml missing hazards mapping")
    if not isinstance(claims, dict):
        raise ValueError("safety_case.yaml missing claims mapping")

    known_reqs = set(requirements.keys())
    known_hazards = set(hazards.keys())
    known_constraints = collect_constraint_ids(root)
    known_properties = collect_property_ids(root)
    known_formal = set(FORMAL_PROPERTY_IDS)

    issues: list[dict[str, str]] = []

    for hazard_id, hazard in sorted(hazards.items()):
        if not isinstance(hazard, dict):
            issues.append({"id": hazard_id, "message": "Hazard entry must be a mapping."})
            continue

        for req in _as_str_list(hazard.get("linked_requirements")):
            if req not in known_reqs:
                issues.append({"id": hazard_id, "message": f"Unknown linked requirement: {req}"})

        controls = hazard.get("controls", {})
        if not isinstance(controls, dict):
            issues.append({"id": hazard_id, "message": "controls must be a mapping."})
            continue

        for control in _as_str_list(controls.get("constraints")):
            if control not in known_constraints:
                issues.append({"id": hazard_id, "message": f"Unknown constraint control: {control}"})
        for control in _as_str_list(controls.get("properties")):
            if control not in known_properties:
                issues.append({"id": hazard_id, "message": f"Unknown property control: {control}"})
        for control in _as_str_list(controls.get("formal")):
            if control not in known_formal:
                issues.append({"id": hazard_id, "message": f"Unknown formal control: {control}"})

    for claim_id, claim in sorted(claims.items()):
        if not isinstance(claim, dict):
            issues.append({"id": claim_id, "message": "Claim entry must be a mapping."})
            continue

        for hazard_id in _as_str_list(claim.get("supported_by_hazards")):
            if hazard_id not in known_hazards:
                issues.append({"id": claim_id, "message": f"Unknown hazard link: {hazard_id}"})

        for req_id in _as_str_list(claim.get("supported_by_requirements")):
            if req_id not in known_reqs:
                issues.append({"id": claim_id, "message": f"Unknown requirement link: {req_id}"})

        for parent in _as_str_list(claim.get("supported_by_claims")):
            if parent not in claims:
                issues.append({"id": claim_id, "message": f"Unknown child claim link: {parent}"})

    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "requirements_path": str(req_path),
            "hazard_log_path": str(hazard_path),
            "safety_case_path": str(case_path),
        },
        "summary": {
            "requirements_total": len(known_reqs),
            "hazards_total": len(known_hazards),
            "claims_total": len(claims),
            "issues_total": len(issues),
        },
        "issues": issues,
        "passed": len(issues) == 0,
    }



def render_safety_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Safety Case Consistency Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Hazards: {report['summary']['hazards_total']}",
        f"- Claims: {report['summary']['claims_total']}",
        f"- Issues: {report['summary']['issues_total']}",
        "",
        "## Issues",
        "",
    ]

    if report["issues"]:
        for issue in report["issues"]:
            lines.append(f"- {issue['id']}: {issue['message']}")
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)

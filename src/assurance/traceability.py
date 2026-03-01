"""Requirements-to-evidence traceability reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.assurance.catalog import collect_constraint_ids, collect_property_ids, load_yaml_mapping, repo_root
from src.assurance.formal_ids import FORMAL_PROPERTY_IDS
from src.common.io_utils import write_json


@dataclass(frozen=True)
class TraceabilityIssue:
    requirement_id: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "requirement_id": self.requirement_id,
            "message": self.message,
        }



def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("Expected list[str] for verification links.")



def _test_file_from_ref(test_ref: str) -> Path:
    file_part = test_ref.split("::", 1)[0]
    return repo_root() / file_part



def build_traceability_report(requirements_path: str | Path | None = None) -> dict[str, Any]:
    root = repo_root()
    req_path = Path(requirements_path) if requirements_path else root / "assurance" / "requirements.yaml"
    raw = load_yaml_mapping(req_path)

    requirements = raw.get("requirements")
    if not isinstance(requirements, dict):
        raise ValueError("requirements.yaml must contain a 'requirements' mapping.")

    constraint_ids = collect_constraint_ids(root)
    property_ids = collect_property_ids(root)
    formal_ids = set(FORMAL_PROPERTY_IDS)

    issues: list[TraceabilityIssue] = []
    rows: list[dict[str, Any]] = []

    for requirement_id in sorted(requirements):
        item = requirements[requirement_id]
        if not isinstance(item, dict):
            issues.append(TraceabilityIssue(requirement_id, "Requirement entry must be a mapping."))
            continue

        statement = item.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            issues.append(TraceabilityIssue(requirement_id, "Missing non-empty statement."))
            statement = ""

        verification = item.get("verification", {})
        if not isinstance(verification, dict):
            issues.append(TraceabilityIssue(requirement_id, "verification must be a mapping."))
            verification = {}

        try:
            linked_constraints = _as_str_list(verification.get("constraints"))
            linked_properties = _as_str_list(verification.get("properties"))
            linked_formal = _as_str_list(verification.get("formal"))
            linked_tests = _as_str_list(verification.get("tests"))
            linked_artifacts = _as_str_list(verification.get("artifacts"))
        except ValueError as exc:
            issues.append(TraceabilityIssue(requirement_id, str(exc)))
            linked_constraints = []
            linked_properties = []
            linked_formal = []
            linked_tests = []
            linked_artifacts = []

        if not (linked_constraints or linked_properties or linked_formal or linked_tests or linked_artifacts):
            issues.append(TraceabilityIssue(requirement_id, "No verification evidence linked."))

        for control in linked_constraints:
            if control not in constraint_ids:
                issues.append(TraceabilityIssue(requirement_id, f"Unknown constraint id: {control}"))

        for prop in linked_properties:
            if prop not in property_ids:
                issues.append(TraceabilityIssue(requirement_id, f"Unknown property id: {prop}"))

        for formal in linked_formal:
            if formal not in formal_ids:
                issues.append(TraceabilityIssue(requirement_id, f"Unknown formal property id: {formal}"))

        for test_ref in linked_tests:
            if not _test_file_from_ref(test_ref).exists():
                issues.append(TraceabilityIssue(requirement_id, f"Test file not found for ref: {test_ref}"))

        req_issues = [issue.message for issue in issues if issue.requirement_id == requirement_id]
        rows.append(
            {
                "id": requirement_id,
                "statement": statement,
                "links": {
                    "constraints": linked_constraints,
                    "properties": linked_properties,
                    "formal": linked_formal,
                    "tests": linked_tests,
                    "artifacts": linked_artifacts,
                },
                "status": "ok" if not req_issues else "issue",
                "issues": req_issues,
            }
        )

    issue_dicts = [issue.as_dict() for issue in issues]
    report = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "requirements_path": str(req_path),
        },
        "catalog": {
            "constraints": sorted(constraint_ids),
            "properties": sorted(property_ids),
            "formal": sorted(formal_ids),
        },
        "summary": {
            "requirements_total": len(rows),
            "requirements_with_issues": len({issue.requirement_id for issue in issues}),
            "issues_total": len(issue_dicts),
            "fully_traced": len({row["id"] for row in rows if row["status"] == "ok"}),
        },
        "requirements": rows,
        "issues": issue_dicts,
        "passed": not issues,
    }
    return report



def render_traceability_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Traceability Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Requirements total: {report['summary']['requirements_total']}",
        f"- Requirements with issues: {report['summary']['requirements_with_issues']}",
        f"- Issues total: {report['summary']['issues_total']}",
        "",
        "## Requirement Matrix",
        "",
        "| Requirement | Constraints | Properties | Formal | Tests | Artifacts | Status |",
        "|---|---|---|---|---|---|---|",
    ]

    for row in report["requirements"]:
        links = row["links"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["id"],
                    ", ".join(links["constraints"]) or "-",
                    ", ".join(links["properties"]) or "-",
                    ", ".join(links["formal"]) or "-",
                    ", ".join(links["tests"]) or "-",
                    ", ".join(links["artifacts"]) or "-",
                    row["status"],
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Issues")
    lines.append("")
    if report["issues"]:
        for issue in report["issues"]:
            lines.append(f"- {issue['requirement_id']}: {issue['message']}")
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)



def write_traceability_outputs(report: dict[str, Any], output_json: str | Path, output_markdown: str | Path) -> None:
    write_json(output_json, report)
    Path(output_markdown).write_text(render_traceability_markdown(report), encoding="utf-8")

"""Diagnostic objects and formatting for MCV."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Diagnostic:
    rule_id: str
    severity: str
    message: str
    path: str
    explanation: str
    suggestion: str | None = None
    line: int | None = None
    column: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)



def format_diagnostic_text(diagnostic: Diagnostic, source_name: str) -> str:
    line = diagnostic.line or 1
    column = diagnostic.column or 1
    parts = [f"{source_name}:{line}:{column}", f"{diagnostic.severity}[{diagnostic.rule_id}]: {diagnostic.message}"]
    if diagnostic.path:
        parts.append(f"path: {diagnostic.path}")
    parts.append("because:")
    parts.append(f"  - {diagnostic.explanation}")
    if diagnostic.suggestion:
        parts.append("suggestion:")
        parts.append(f"  - {diagnostic.suggestion}")
    return "\n".join(parts)

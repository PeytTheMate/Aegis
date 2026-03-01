"""High-level MCV operations used by CLI and pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.mcv.compiler import CompiledArtifact, create_compiled_artifact, load_compiled_artifact, write_compiled_artifact
from src.mcv.diffing import semantic_diff
from src.mcv.loader import load_mission
from src.mcv.validator import ValidationResult, validate_mission


@dataclass(frozen=True)
class ExplainResult:
    validation: ValidationResult



def validate_file(path: str | Path) -> ValidationResult:
    loaded = load_mission(path)
    return validate_mission(loaded)



def compile_file(path: str | Path, output: str | Path | None = None) -> tuple[ValidationResult, CompiledArtifact | None]:
    validation = validate_file(path)
    if not validation.valid:
        return validation, None
    artifact = create_compiled_artifact(validation.normalized_config, source=str(path))
    if output is not None:
        write_compiled_artifact(output, artifact)
    return validation, artifact



def explain_file(path: str | Path) -> ExplainResult:
    return ExplainResult(validation=validate_file(path))



def diff_files(path_a: str | Path, path_b: str | Path) -> tuple[ValidationResult, ValidationResult, list[dict[str, Any]]]:
    result_a = validate_file(path_a)
    result_b = validate_file(path_b)
    if not result_a.valid or not result_b.valid:
        return result_a, result_b, []
    return result_a, result_b, semantic_diff(result_a.normalized_config, result_b.normalized_config)



def load_compiled(path: str | Path) -> dict[str, Any]:
    return load_compiled_artifact(path)

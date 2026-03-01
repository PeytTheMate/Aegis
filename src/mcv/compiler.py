"""Compiled mission artifact generation and loading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.hash_utils import sha256_json
from src.common.io_utils import read_text, write_json
from src.common.version import TOOL_VERSION
from src.mcv.schema import FIELD_SPECS


@dataclass(frozen=True)
class CompiledArtifact:
    artifact: dict[str, Any]



def create_compiled_artifact(normalized_config: dict[str, Any], source: str | None = None) -> CompiledArtifact:
    serializable_fields: dict[str, dict[str, Any]] = {}
    for path, spec in FIELD_SPECS.items():
        serializable_fields[path] = {
            key: (
                value.__name__
                if isinstance(value, type)
                else [item.__name__ if isinstance(item, type) else item for item in value]
                if isinstance(value, tuple)
                else sorted(value)
                if isinstance(value, set)
                else value
            )
            for key, value in spec.items()
        }

    schema_descriptor = {
        "fields": serializable_fields,
        "schema_version": 1,
    }
    schema_hash = sha256_json(schema_descriptor)
    config_hash = sha256_json(normalized_config)

    artifact = {
        "artifact_version": 1,
        "schema_hash": schema_hash,
        "config_hash": config_hash,
        "tool_version": TOOL_VERSION,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": source,
        "canonical_config": normalized_config,
    }
    return CompiledArtifact(artifact=artifact)



def write_compiled_artifact(path: str | Path, compiled: CompiledArtifact) -> None:
    write_json(path, compiled.artifact)



def load_compiled_artifact(path: str | Path) -> dict[str, Any]:
    payload = read_text(path)
    import json

    parsed = json.loads(payload)
    if not isinstance(parsed, dict) or "canonical_config" not in parsed:
        raise ValueError("Invalid compiled artifact.")
    return parsed

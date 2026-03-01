"""Shared catalog and loading helpers for assurance tooling."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.common.io_utils import read_text
from src.mcv.simple_yaml import YAMLParseError, parse_yaml



def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]



def load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    try:
        parsed = parse_yaml(read_text(path)).payload
    except YAMLParseError as exc:
        raise ValueError(f"Invalid YAML at {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"YAML at {path} must be a mapping.")
    return parsed



def _collect_ids_from_file(path: Path, pattern: str) -> set[str]:
    text = read_text(path)
    return set(re.findall(pattern, text))



def collect_constraint_ids(root: Path | None = None) -> set[str]:
    base = root or repo_root()
    return _collect_ids_from_file(base / "src" / "mcv" / "validator.py", r"MCV-\d{3}")



def collect_property_ids(root: Path | None = None) -> set[str]:
    base = root or repo_root()
    return _collect_ids_from_file(base / "src" / "pbt" / "properties.py", r"PBT-\d{3}")

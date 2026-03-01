"""Mission file loader for YAML/JSON input."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common.io_utils import read_text
from src.mcv.pathing import iter_paths
from src.mcv.simple_yaml import ParsedDocument, YAMLParseError, parse_yaml


class LoadError(ValueError):
    """Raised when mission files cannot be parsed."""


@dataclass(frozen=True)
class LoadedMission:
    payload: dict[str, Any]
    line_map: dict[str, int]
    source: str
    explicit_paths: set[str]



def _collect_explicit_paths(payload: dict[str, Any]) -> set[str]:
    return {path for path in iter_paths(payload) if path}



def _parse_payload(text: str, source: str) -> ParsedDocument:
    if source.endswith(".json"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LoadError(f"Invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LoadError("Top-level JSON must be an object.")
        return ParsedDocument(payload=parsed, line_map={})

    try:
        return parse_yaml(text)
    except YAMLParseError as exc:
        raise LoadError(str(exc)) from exc



def load_mission(path: str | Path) -> LoadedMission:
    source = str(path)
    text = read_text(source)
    parsed = _parse_payload(text, source)
    return LoadedMission(
        payload=parsed.payload,
        line_map=parsed.line_map,
        source=source,
        explicit_paths=_collect_explicit_paths(parsed.payload),
    )

"""Nested path helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any



def flatten_paths(payload: Any, prefix: tuple[str, ...] = ()) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    if isinstance(payload, dict):
        for key in sorted(payload):
            flattened.update(flatten_paths(payload[key], prefix + (str(key),)))
        return flattened
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            flattened.update(flatten_paths(item, prefix + (str(index),)))
        if not payload:
            flattened[".".join(prefix)] = []
        return flattened
    flattened[".".join(prefix)] = payload
    return flattened



def set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor: dict[str, Any] = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value



def get_path(payload: dict[str, Any], path: str) -> Any:
    cursor: Any = payload
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            raise KeyError(path)
        cursor = cursor[part]
    return cursor



def has_path(payload: dict[str, Any], path: str) -> bool:
    try:
        get_path(payload, path)
        return True
    except KeyError:
        return False



def iter_paths(payload: Any, prefix: tuple[str, ...] = ()) -> Iterable[str]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield from iter_paths(value, prefix + (str(key),))
        return
    if isinstance(payload, list):
        yield ".".join(prefix)
        return
    yield ".".join(prefix)

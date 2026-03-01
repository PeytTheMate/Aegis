"""Semantic diffing for normalized mission configs."""

from __future__ import annotations

import math
from typing import Any

from src.mcv.pathing import flatten_paths



def _equivalent(left: Any, right: Any) -> bool:
    if isinstance(left, float) and isinstance(right, float):
        return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-9)
    return left == right


def semantic_diff(config_a: dict[str, Any], config_b: dict[str, Any]) -> list[dict[str, Any]]:
    flat_a = flatten_paths(config_a)
    flat_b = flatten_paths(config_b)

    differences: list[dict[str, Any]] = []
    all_paths = sorted(set(flat_a) | set(flat_b))
    for path in all_paths:
        left = flat_a.get(path, "<missing>")
        right = flat_b.get(path, "<missing>")
        if not _equivalent(left, right):
            differences.append(
                {
                    "path": path,
                    "a": left,
                    "b": right,
                }
            )
    return differences

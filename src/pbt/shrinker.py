"""Failure scenario shrinking logic."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable



def _numeric_keys(fault: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for key, value in fault.items():
        if key in {"start", "end"}:
            continue
        if isinstance(value, (int, float)):
            keys.append(key)
    return keys



def shrink_scenario(initial: dict[str, Any], fails: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    current = deepcopy(initial)

    while current["duration_s"] > 5.0:
        candidate = deepcopy(current)
        candidate["duration_s"] = round(max(5.0, candidate["duration_s"] / 2.0), 3)
        candidate["faults"] = [
            {
                **fault,
                "start": min(float(fault.get("start", 0.0)), candidate["duration_s"]),
                "end": min(float(fault.get("end", candidate["duration_s"])), candidate["duration_s"]),
            }
            for fault in candidate.get("faults", [])
            if float(fault.get("start", 0.0)) <= candidate["duration_s"]
        ]
        if fails(candidate):
            current = candidate
        else:
            break

    index = 0
    while index < len(current.get("faults", [])):
        candidate = deepcopy(current)
        candidate["faults"].pop(index)
        if fails(candidate):
            current = candidate
        else:
            index += 1

    for i, fault in enumerate(list(current.get("faults", []))):
        for key in _numeric_keys(fault):
            while True:
                candidate = deepcopy(current)
                old_val = float(candidate["faults"][i][key])
                new_val = round(old_val / 2.0, 6)
                if new_val == old_val:
                    break
                candidate["faults"][i][key] = new_val
                if fails(candidate):
                    current = candidate
                else:
                    break

    return current

"""Unit parsing and normalization helpers."""

from __future__ import annotations

import math
import re

_UNIT_PATTERN = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*([A-Za-z/]+)\s*$")

_UNIT_CONVERSIONS = {
    "deg": lambda value: value * math.pi / 180.0,
    "rad": lambda value: value,
    "ms": lambda value: value / 1000.0,
    "s": lambda value: value,
    "Pa": lambda value: value,
    "deg/s": lambda value: value * math.pi / 180.0,
    "rad/s": lambda value: value,
}


class UnitError(ValueError):
    """Raised when a unitful value is malformed or unsupported."""



def parse_unit_value(raw: str | int | float, expected_units: tuple[str, ...]) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str):
        raise UnitError(f"Expected numeric or unit string, got {type(raw).__name__}")

    match = _UNIT_PATTERN.match(raw)
    if not match:
        raise UnitError(f"Malformed unit value: {raw}")

    magnitude = float(match.group(1))
    unit = match.group(2)
    if unit not in expected_units:
        expected = ", ".join(expected_units)
        raise UnitError(f"Unsupported unit '{unit}', expected one of: {expected}")
    if unit not in _UNIT_CONVERSIONS:
        raise UnitError(f"Missing conversion for unit '{unit}'")
    return _UNIT_CONVERSIONS[unit](magnitude)

"""A small YAML subset parser used to avoid external dependencies.

Supported constructs:
- Nested mappings with indentation
- Lists via `- item`
- Inline lists like `["imu", "gps"]`
- Scalars: quoted strings, bool, null, int, float
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class YAMLParseError(ValueError):
    """Raised when an input YAML document is not supported."""


@dataclass(frozen=True)
class ParsedDocument:
    payload: dict[str, Any]
    line_map: dict[str, int]


@dataclass(frozen=True)
class _Line:
    number: int
    indent: int
    text: str



def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    result: list[str] = []
    for char in line:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            result.append(char)
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            result.append(char)
            continue
        if char == "#" and not in_single and not in_double:
            break
        result.append(char)
    return "".join(result).rstrip()



def _tokenize(text: str) -> list[_Line]:
    lines: list[_Line] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw:
            raise YAMLParseError(f"Tabs are not supported (line {number}).")
        stripped = _strip_comment(raw)
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        lines.append(_Line(number=number, indent=indent, text=stripped.strip()))
    return lines



def _split_top_level(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth_square = 0
    depth_curly = 0
    in_single = False
    in_double = False
    escaped = False

    for char in text:
        if escaped:
            buf.append(char)
            escaped = False
            continue
        if char == "\\":
            buf.append(char)
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            buf.append(char)
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            buf.append(char)
            continue
        if in_single or in_double:
            buf.append(char)
            continue
        if char == "[":
            depth_square += 1
            buf.append(char)
            continue
        if char == "]":
            depth_square -= 1
            buf.append(char)
            continue
        if char == "{":
            depth_curly += 1
            buf.append(char)
            continue
        if char == "}":
            depth_curly -= 1
            buf.append(char)
            continue
        if char == delimiter and depth_square == 0 and depth_curly == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(char)

    parts.append("".join(buf).strip())
    return [part for part in parts if part]



def _parse_scalar(token: str) -> Any:
    token = token.strip()
    if token.startswith("[") and token.endswith("]"):
        inner = token[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_top_level(inner, ",")]

    if token.startswith("{") and token.endswith("}"):
        inner = token[1:-1].strip()
        parsed: dict[str, Any] = {}
        if not inner:
            return parsed
        for entry in _split_top_level(inner, ","):
            if ":" not in entry:
                raise YAMLParseError(f"Invalid inline map entry: {entry}")
            key, value = entry.split(":", 1)
            parsed[key.strip()] = _parse_scalar(value.strip())
        return parsed

    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        return token[1:-1]

    lowered = token.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "~"}:
        return None

    try:
        if token.startswith("0") and token not in {"0", "0.0"} and not token.startswith("0."):
            raise ValueError
        return int(token)
    except ValueError:
        pass

    try:
        return float(token)
    except ValueError:
        return token



def _split_key_value(text: str) -> tuple[str, str | None]:
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == ":" and not in_single and not in_double:
            key = text[:index].strip()
            value = text[index + 1 :].strip()
            return key, value if value else None
    raise YAMLParseError(f"Expected key:value pair: {text}")



def _parse_block(lines: list[_Line], start: int, indent: int, path: tuple[str, ...], line_map: dict[str, int]) -> tuple[Any, int]:
    if start >= len(lines):
        return {}, start

    is_list = lines[start].indent == indent and lines[start].text.startswith("- ")

    if is_list:
        items: list[Any] = []
        index = start
        while index < len(lines):
            line = lines[index]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise YAMLParseError(f"Unexpected indentation at line {line.number}")
            if not line.text.startswith("- "):
                break
            remainder = line.text[2:].strip()
            item_path = path + (str(len(items)),)
            if remainder:
                if ":" in remainder and not remainder.startswith("{") and not remainder.startswith("["):
                    key, value = _split_key_value(remainder)
                    entry: dict[str, Any] = {}
                    entry[key] = _parse_scalar(value) if value is not None else {}
                    line_map[".".join(item_path + (key,))] = line.number
                    index += 1
                    if value is None and index < len(lines) and lines[index].indent > indent:
                        nested, index = _parse_block(lines, index, lines[index].indent, item_path + (key,), line_map)
                        entry[key] = nested
                    items.append(entry)
                    continue
                items.append(_parse_scalar(remainder))
                line_map[".".join(item_path)] = line.number
                index += 1
                continue

            index += 1
            if index >= len(lines) or lines[index].indent <= indent:
                items.append({})
                line_map[".".join(item_path)] = line.number
                continue
            nested, index = _parse_block(lines, index, lines[index].indent, item_path, line_map)
            items.append(nested)
            line_map[".".join(item_path)] = line.number
        return items, index

    mapping: dict[str, Any] = {}
    index = start
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise YAMLParseError(f"Unexpected indentation at line {line.number}")
        if line.text.startswith("- "):
            break

        key, value = _split_key_value(line.text)
        if not key:
            raise YAMLParseError(f"Missing key at line {line.number}")
        key_path = path + (key,)
        line_map[".".join(key_path)] = line.number

        if value is None:
            index += 1
            if index >= len(lines) or lines[index].indent <= indent:
                mapping[key] = {}
                continue
            nested, index = _parse_block(lines, index, lines[index].indent, key_path, line_map)
            mapping[key] = nested
            continue

        mapping[key] = _parse_scalar(value)
        index += 1

    return mapping, index



def parse_yaml(text: str) -> ParsedDocument:
    lines = _tokenize(text)
    if not lines:
        return ParsedDocument(payload={}, line_map={})
    line_map: dict[str, int] = {}
    payload, index = _parse_block(lines, 0, lines[0].indent, tuple(), line_map)
    if index != len(lines):
        raise YAMLParseError(f"Unable to parse full document (stopped at line {lines[index].number}).")
    if not isinstance(payload, dict):
        raise YAMLParseError("Top-level YAML value must be a mapping.")
    return ParsedDocument(payload=payload, line_map=dict(sorted(line_map.items())))

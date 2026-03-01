"""Typed normalization and semantic validation for mission configs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.mcv.diagnostics import Diagnostic
from src.mcv.loader import LoadedMission
from src.mcv.pathing import get_path, has_path, set_path
from src.mcv.schema import FIELD_SPECS, default_config
from src.mcv.units import UnitError, parse_unit_value


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    normalized_config: dict[str, Any]
    diagnostics: list[Diagnostic]
    source: str
    line_map: dict[str, int]
    explicit_paths: set[str]



def _deep_merge_known(base: dict[str, Any], override: dict[str, Any], path: str, diagnostics: list[Diagnostic], line_map: dict[str, int]) -> None:
    for key, value in override.items():
        next_path = f"{path}.{key}" if path else key
        if key not in base:
            diagnostics.append(
                Diagnostic(
                    rule_id="MCV-000",
                    severity="error",
                    message="unknown field",
                    path=next_path,
                    explanation=f"Field '{next_path}' is not part of the supported mission schema.",
                    suggestion="remove or rename the field",
                    line=line_map.get(next_path),
                    column=1,
                )
            )
            continue

        if isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge_known(base[key], value, next_path, diagnostics, line_map)
        else:
            base[key] = value



def _normalize_field(path: str, merged: dict[str, Any], diagnostics: list[Diagnostic], line_map: dict[str, int]) -> None:
    spec = FIELD_SPECS[path]
    value = get_path(merged, path)
    expected_type = spec["type"]

    if expected_type is float:
        if not isinstance(value, (int, float, str)):
            diagnostics.append(
                Diagnostic(
                    rule_id="MCV-001",
                    severity="error",
                    message="invalid numeric field type",
                    path=path,
                    explanation=f"Expected numeric value for '{path}', got {type(value).__name__}.",
                    suggestion="provide a numeric literal or unit string",
                    line=line_map.get(path),
                    column=1,
                )
            )
            return
        if "units" in spec:
            try:
                set_path(merged, path, parse_unit_value(value, spec["units"]))
            except UnitError as exc:
                diagnostics.append(
                    Diagnostic(
                        rule_id="MCV-002",
                        severity="error",
                        message="invalid unit value",
                        path=path,
                        explanation=str(exc),
                        suggestion="use a supported unit for this field",
                        line=line_map.get(path),
                        column=1,
                    )
                )
                return
        else:
            set_path(merged, path, float(value))

    elif expected_type is bool:
        if not isinstance(value, bool):
            diagnostics.append(
                Diagnostic(
                    rule_id="MCV-003",
                    severity="error",
                    message="invalid boolean field type",
                    path=path,
                    explanation=f"Expected bool for '{path}', got {type(value).__name__}.",
                    suggestion="set this field to true or false",
                    line=line_map.get(path),
                    column=1,
                )
            )
            return

    elif expected_type is int:
        if not isinstance(value, int):
            diagnostics.append(
                Diagnostic(
                    rule_id="MCV-004",
                    severity="error",
                    message="invalid integer field type",
                    path=path,
                    explanation=f"Expected int for '{path}', got {type(value).__name__}.",
                    suggestion="provide an integer",
                    line=line_map.get(path),
                    column=1,
                )
            )
            return

    elif expected_type is str:
        if not isinstance(value, str):
            diagnostics.append(
                Diagnostic(
                    rule_id="MCV-005",
                    severity="error",
                    message="invalid string field type",
                    path=path,
                    explanation=f"Expected str for '{path}', got {type(value).__name__}.",
                    suggestion="provide a quoted string",
                    line=line_map.get(path),
                    column=1,
                )
            )
            return

    elif expected_type is list:
        if not isinstance(value, list):
            diagnostics.append(
                Diagnostic(
                    rule_id="MCV-006",
                    severity="error",
                    message="invalid list field type",
                    path=path,
                    explanation=f"Expected list for '{path}', got {type(value).__name__}.",
                    suggestion="provide a YAML/JSON list",
                    line=line_map.get(path),
                    column=1,
                )
            )
            return
        item_type = spec.get("item_type")
        if item_type is not None:
            for index, item in enumerate(value):
                if not isinstance(item, item_type):
                    diagnostics.append(
                        Diagnostic(
                            rule_id="MCV-007",
                            severity="error",
                            message="invalid list item type",
                            path=f"{path}.{index}",
                            explanation=f"Expected {item_type.__name__}, got {type(item).__name__}.",
                            suggestion="update list item type",
                            line=line_map.get(path),
                            column=1,
                        )
                    )
                    return

    allowed = spec.get("allowed")
    if allowed is not None and get_path(merged, path) not in allowed:
        diagnostics.append(
            Diagnostic(
                rule_id="MCV-008",
                severity="error",
                message="invalid enum value",
                path=path,
                explanation=f"Value must be one of: {sorted(allowed)}.",
                suggestion="choose a supported value",
                line=line_map.get(path),
                column=1,
            )
        )



def _constraint(path: str, rule_id: str, message: str, explanation: str, diagnostics: list[Diagnostic], line_map: dict[str, int], suggestion: str | None = None) -> None:
    diagnostics.append(
        Diagnostic(
            rule_id=rule_id,
            severity="error",
            message=message,
            path=path,
            explanation=explanation,
            suggestion=suggestion,
            line=line_map.get(path),
            column=1,
        )
    )



def _validate_constraints(config: dict[str, Any], diagnostics: list[Diagnostic], line_map: dict[str, int]) -> None:
    packet_loss_budget = float(get_path(config, "comms.packet_loss_budget"))
    if not (0.0 <= packet_loss_budget <= 0.10):
        _constraint(
            "comms.packet_loss_budget",
            "MCV-014",
            "packet loss budget out of range",
            f"packet_loss_budget={packet_loss_budget:.4f} must be in [0.0, 0.10].",
            diagnostics,
            line_map,
            suggestion="set packet_loss_budget between 0 and 0.10",
        )

    imu_enabled = bool(get_path(config, "navigation.imu.enabled"))
    gps_enabled = bool(get_path(config, "navigation.gps.enabled"))
    if not (imu_enabled or gps_enabled):
        _constraint(
            "navigation",
            "MCV-015",
            "at least one navigation sensor must be enabled",
            "Both IMU and GPS are disabled, leaving no navigation source.",
            diagnostics,
            line_map,
            suggestion="enable imu or gps",
        )

    allow_autonomous_abort = bool(get_path(config, "control.mode_logic.allow_autonomous_abort"))
    abort_requires = get_path(config, "control.mode_logic.abort_requires")
    if allow_autonomous_abort and not imu_enabled:
        _constraint(
            "control.mode_logic.allow_autonomous_abort",
            "MCV-016",
            "autonomous abort requires IMU",
            "allow_autonomous_abort is true while navigation.imu.enabled is false.",
            diagnostics,
            line_map,
            suggestion="enable navigation.imu",
        )
    if allow_autonomous_abort and "imu" not in abort_requires:
        _constraint(
            "control.mode_logic.abort_requires",
            "MCV-017",
            "autonomous abort dependency missing",
            "abort_requires does not include 'imu' while autonomous abort is enabled.",
            diagnostics,
            line_map,
            suggestion="add 'imu' to abort_requires",
        )

    max_aoa = float(get_path(config, "guidance.max_angle_of_attack"))
    if not (0.01 <= max_aoa <= 0.60):
        _constraint(
            "guidance.max_angle_of_attack",
            "MCV-018",
            "max angle of attack outside safe envelope",
            f"max_angle_of_attack={max_aoa:.5f} rad is outside [0.01, 0.60].",
            diagnostics,
            line_map,
            suggestion="set AoA limit within safe range",
        )

    imu_latency = float(get_path(config, "navigation.imu.max_latency"))
    gps_latency = float(get_path(config, "navigation.gps.max_latency"))
    if imu_latency > 0.250:
        _constraint(
            "navigation.imu.max_latency",
            "MCV-019",
            "imu latency exceeds bound",
            f"imu.max_latency={imu_latency:.3f}s exceeds 0.250s limit.",
            diagnostics,
            line_map,
            suggestion="reduce IMU latency budget",
        )
    if gps_latency > 1.0:
        _constraint(
            "navigation.gps.max_latency",
            "MCV-020",
            "gps latency exceeds bound",
            f"gps.max_latency={gps_latency:.3f}s exceeds 1.0s limit.",
            diagnostics,
            line_map,
            suggestion="reduce GPS latency budget",
        )

    max_skew = float(get_path(config, "comms.time_sync.max_skew"))
    if max_skew > 0.050:
        _constraint(
            "comms.time_sync.max_skew",
            "MCV-021",
            "time sync skew exceeds bound",
            f"time_sync.max_skew={max_skew:.3f}s exceeds 0.050s limit.",
            diagnostics,
            line_map,
            suggestion="tighten comms.time_sync.max_skew",
        )

    authority = float(get_path(config, "control.actuator.max_gimbal_rate")) * float(
        get_path(config, "control.actuator.max_gimbal_angle")
    )
    if authority > 0.075:
        _constraint(
            "control.actuator",
            "MCV-022",
            "actuator authority exceeds safe envelope",
            f"max_gimbal_rate * max_gimbal_angle = {authority:.5f} rad^2/s exceeds 0.075.",
            diagnostics,
            line_map,
            suggestion="reduce gimbal rate or angle limit",
        )



def validate_mission(loaded: LoadedMission) -> ValidationResult:
    diagnostics: list[Diagnostic] = []
    merged = default_config()

    _deep_merge_known(merged, loaded.payload, "", diagnostics, loaded.line_map)

    for path in sorted(FIELD_SPECS):
        if not has_path(merged, path):
            diagnostics.append(
                Diagnostic(
                    rule_id="MCV-009",
                    severity="error",
                    message="missing required field",
                    path=path,
                    explanation=f"Field '{path}' is required by schema.",
                    suggestion="provide this field",
                    line=loaded.line_map.get(path),
                    column=1,
                )
            )
            continue
        _normalize_field(path, merged, diagnostics, loaded.line_map)

    if not diagnostics:
        _validate_constraints(merged, diagnostics, loaded.line_map)

    return ValidationResult(
        valid=not diagnostics,
        normalized_config=merged,
        diagnostics=diagnostics,
        source=loaded.source,
        line_map=loaded.line_map,
        explicit_paths=loaded.explicit_paths,
    )

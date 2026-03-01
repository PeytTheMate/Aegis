"""Executable bounded state-space verification for mode-logic properties.

This checker explores all input traces up to a finite horizon and reports
counterexamples. It is aligned with the TLA+ specification but does not
invoke TLC directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from typing import Any

from src.assurance.formal_ids import FORMAL_PROPERTY_IDS

_ALLOWED_MODES = ("NOMINAL", "ABORT_PENDING", "ABORT")


@dataclass(frozen=True)
class State:
    mode: str
    abort_requested: bool
    pending_steps: int



def _next_state(state: State, hazard_detected: bool, imu_healthy: bool, abort_delay_steps: int, allow_abort_exit: bool) -> State:
    mode = state.mode
    abort_requested = state.abort_requested
    pending_steps = state.pending_steps

    if mode == "ABORT":
        if allow_abort_exit and not hazard_detected:
            return State(mode="NOMINAL", abort_requested=False, pending_steps=0)
        return state

    if hazard_detected and imu_healthy:
        abort_requested = True

    if mode == "NOMINAL" and abort_requested:
        return State(mode="ABORT_PENDING", abort_requested=abort_requested, pending_steps=0)

    if mode == "ABORT_PENDING":
        pending_steps += 1
        if pending_steps >= abort_delay_steps:
            return State(mode="ABORT", abort_requested=abort_requested, pending_steps=pending_steps)
        return State(mode="ABORT_PENDING", abort_requested=abort_requested, pending_steps=pending_steps)

    return State(mode="NOMINAL", abort_requested=abort_requested, pending_steps=0)



def verify_mode_logic(
    horizon_steps: int = 8,
    abort_delay_steps: int = 3,
    abort_deadline_steps: int = 4,
    assume_imu_healthy: bool = True,
    allow_abort_exit: bool = False,
) -> dict[str, Any]:
    if abort_delay_steps <= 0:
        raise ValueError("abort_delay_steps must be positive")
    if horizon_steps <= 0:
        raise ValueError("horizon_steps must be positive")

    failures: dict[str, list[dict[str, Any]]] = {pid: [] for pid in FORMAL_PROPERTY_IDS}
    checked_paths = 0

    initial = State(mode="NOMINAL", abort_requested=False, pending_steps=0)
    imu_values = [True] if assume_imu_healthy else [False, True]

    for input_trace in product(product([False, True], imu_values), repeat=horizon_steps):
        checked_paths += 1
        state = initial
        hazard_due_steps: list[int] = []
        history: list[dict[str, Any]] = []

        for step, (hazard_detected, imu_healthy) in enumerate(input_trace):
            history.append(
                {
                    "step": step,
                    "mode": state.mode,
                    "abort_requested": state.abort_requested,
                    "pending_steps": state.pending_steps,
                    "hazard_detected": hazard_detected,
                    "imu_healthy": imu_healthy,
                }
            )

            if state.mode not in _ALLOWED_MODES and not failures["FML-001"]:
                failures["FML-001"].append(list(history))

            if hazard_detected and imu_healthy:
                hazard_due_steps.append(step + abort_deadline_steps)

            next_state = _next_state(state, hazard_detected, imu_healthy, abort_delay_steps, allow_abort_exit)

            if state.mode == "ABORT" and next_state.mode != "ABORT" and not failures["FML-002"]:
                failures["FML-002"].append(list(history))

            if next_state.mode == "ABORT":
                hazard_due_steps = []
            else:
                expired = [due for due in hazard_due_steps if step + 1 >= due]
                if expired and not failures["FML-003"]:
                    failures["FML-003"].append(list(history))

            state = next_state

        history.append(
            {
                "step": horizon_steps,
                "mode": state.mode,
                "abort_requested": state.abort_requested,
                "pending_steps": state.pending_steps,
                "hazard_detected": False,
                "imu_healthy": imu_values[0],
            }
        )

        if state.mode not in _ALLOWED_MODES and not failures["FML-001"]:
            failures["FML-001"].append(list(history))

    property_results: list[dict[str, Any]] = []
    for property_id in sorted(FORMAL_PROPERTY_IDS):
        property_results.append(
            {
                "property_id": property_id,
                "passed": len(failures[property_id]) == 0,
                "counterexample": failures[property_id][0] if failures[property_id] else None,
            }
        )

    passed = all(item["passed"] for item in property_results)
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "checked_paths": checked_paths,
        "parameters": {
            "horizon_steps": horizon_steps,
            "abort_delay_steps": abort_delay_steps,
            "abort_deadline_steps": abort_deadline_steps,
            "assume_imu_healthy": assume_imu_healthy,
            "allow_abort_exit": allow_abort_exit,
        },
        "properties": property_results,
        "passed": passed,
    }



def render_formal_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Formal Mode Logic Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Checked paths: {report['checked_paths']}",
        f"- Passed: {report['passed']}",
        "",
        "## Property Results",
        "",
    ]
    for item in report["properties"]:
        lines.append(f"- {item['property_id']}: {'pass' if item['passed'] else 'fail'}")
        if item["counterexample"] is not None:
            lines.append(f"  - counterexample length: {len(item['counterexample'])}")
    lines.append("")
    return "\n".join(lines)

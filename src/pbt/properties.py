"""Property checks for simulation traces."""

from __future__ import annotations

from typing import Any



def evaluate_properties(trace: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    max_aoa = float(config["guidance"]["max_angle_of_attack"])
    for row in trace:
        if abs(float(row["aoa_rad"])) > max_aoa:
            violations.append(
                {
                    "property_id": "PBT-001",
                    "message": "AoA exceeds configured max",
                    "time_s": row["time_s"],
                    "details": {
                        "aoa_rad": row["aoa_rad"],
                        "max_aoa_rad": max_aoa,
                    },
                }
            )
            break

    request_times = [float(row["time_s"]) for row in trace if bool(row["abort_requested"]) is True]
    if request_times:
        first_request = min(request_times)
        deadline = first_request + 2.0
        entered_abort = any(
            row["mode"] == "ABORT" and float(row["time_s"]) <= deadline
            for row in trace
        )
        if not entered_abort:
            violations.append(
                {
                    "property_id": "PBT-002",
                    "message": "Abort mode not entered within 2s of request",
                    "time_s": first_request,
                    "details": {"deadline": deadline},
                }
            )

    for row in trace:
        if not bool(row["is_finite"]):
            violations.append(
                {
                    "property_id": "PBT-003",
                    "message": "Controller output is non-finite",
                    "time_s": row["time_s"],
                    "details": {},
                }
            )
            break

    prev_mode = trace[0]["mode"] if trace else "NOMINAL"
    for row in trace[1:]:
        mode = row["mode"]
        if prev_mode == "ABORT" and mode != "ABORT":
            violations.append(
                {
                    "property_id": "PBT-004",
                    "message": "Invalid state transition from ABORT",
                    "time_s": row["time_s"],
                    "details": {"from": prev_mode, "to": mode},
                }
            )
            break
        prev_mode = mode

    # PBT-005: State estimation error bounded (requires Kalman filter fields)
    if trace and "estimated_aoa_rad" in trace[0]:
        max_estimation_error = 0.15  # ~8.6 degrees
        for row in trace:
            error = abs(float(row["aoa_rad"]) - float(row["estimated_aoa_rad"]))
            if error > max_estimation_error:
                violations.append(
                    {
                        "property_id": "PBT-005",
                        "message": "State estimation error exceeds threshold",
                        "time_s": row["time_s"],
                        "details": {
                            "true_aoa_rad": row["aoa_rad"],
                            "estimated_aoa_rad": row["estimated_aoa_rad"],
                            "error_rad": error,
                            "threshold_rad": max_estimation_error,
                        },
                    }
                )
                break

    return violations

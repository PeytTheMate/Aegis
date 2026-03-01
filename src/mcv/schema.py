"""Mission schema defaults and field metadata."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "vehicle": "falcon_like",
    "mission_id": "UNSET",
    "guidance": {
        "enabled": True,
        "max_angle_of_attack": "10 deg",
        "max_q": "65000 Pa",
    },
    "navigation": {
        "imu": {
            "enabled": True,
            "max_latency": "20 ms",
        },
        "gps": {
            "enabled": True,
            "max_latency": "250 ms",
        },
    },
    "control": {
        "actuator": {
            "max_gimbal_rate": "8 deg/s",
            "max_gimbal_angle": "15 deg",
        },
        "mode_logic": {
            "allow_autonomous_abort": False,
            "abort_requires": ["imu"],
        },
    },
    "comms": {
        "packet_loss_budget": 0.02,
        "time_sync": {
            "max_skew": "5 ms",
        },
    },
}

FIELD_SPECS: dict[str, dict[str, Any]] = {
    "schema_version": {"type": int, "allowed": {1}},
    "vehicle": {"type": str, "allowed": {"falcon_like"}},
    "mission_id": {"type": str},
    "guidance.enabled": {"type": bool},
    "guidance.max_angle_of_attack": {"type": float, "units": ("deg", "rad")},
    "guidance.max_q": {"type": float, "units": ("Pa",)},
    "navigation.imu.enabled": {"type": bool},
    "navigation.imu.max_latency": {"type": float, "units": ("ms", "s")},
    "navigation.gps.enabled": {"type": bool},
    "navigation.gps.max_latency": {"type": float, "units": ("ms", "s")},
    "control.actuator.max_gimbal_rate": {"type": float, "units": ("deg/s", "rad/s")},
    "control.actuator.max_gimbal_angle": {"type": float, "units": ("deg", "rad")},
    "control.mode_logic.allow_autonomous_abort": {"type": bool},
    "control.mode_logic.abort_requires": {"type": list, "item_type": str},
    "comms.packet_loss_budget": {"type": float},
    "comms.time_sync.max_skew": {"type": float, "units": ("ms", "s")},
}

BASE_UNIT_KEYS = {
    "guidance.max_angle_of_attack": "rad",
    "guidance.max_q": "Pa",
    "navigation.imu.max_latency": "s",
    "navigation.gps.max_latency": "s",
    "control.actuator.max_gimbal_rate": "rad/s",
    "control.actuator.max_gimbal_angle": "rad",
    "comms.time_sync.max_skew": "s",
}



def default_config() -> dict[str, Any]:
    return deepcopy(DEFAULT_CONFIG)

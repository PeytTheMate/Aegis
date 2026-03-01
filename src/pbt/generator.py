"""Scenario generation for property-based tests."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScenarioProfile:
    duration_range: tuple[float, float]
    fault_count_range: tuple[int, int]
    disturbance_range: tuple[float, float]
    packet_loss_rate_range: tuple[float, float]
    imu_bias_range: tuple[float, float]
    latency_spike_range: tuple[float, float]


PROFILES: dict[str, ScenarioProfile] = {
    "nominal": ScenarioProfile(
        duration_range=(60.0, 120.0),
        fault_count_range=(1, 3),
        disturbance_range=(0.005, 0.08),
        packet_loss_rate_range=(0.01, 0.08),
        imu_bias_range=(0.001, 0.08),
        latency_spike_range=(0.01, 0.15),
    ),
    "degraded": ScenarioProfile(
        duration_range=(80.0, 160.0),
        fault_count_range=(2, 5),
        disturbance_range=(0.08, 0.35),
        packet_loss_rate_range=(0.08, 0.25),
        imu_bias_range=(0.05, 0.35),
        latency_spike_range=(0.10, 0.60),
    ),
}



def _uniform(rng: random.Random, bounds: tuple[float, float]) -> float:
    return rng.uniform(bounds[0], bounds[1])



def generate_scenario(seed: int, profile: str = "nominal") -> dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'.")

    rng = random.Random(seed)
    profile_spec = PROFILES[profile]
    duration = round(_uniform(rng, profile_spec.duration_range), 3)
    fault_count = rng.randint(*profile_spec.fault_count_range)

    faults: list[dict[str, Any]] = []
    available_types = ["imu_bias", "packet_loss", "disturbance", "latency_spike", "mode_churn"]

    for _ in range(fault_count):
        fault_type = rng.choice(available_types)
        start = round(rng.uniform(0.0, max(1.0, duration - 5.0)), 3)
        end = round(rng.uniform(start + 1.0, duration), 3)

        if fault_type == "imu_bias":
            faults.append(
                {
                    "type": fault_type,
                    "start": start,
                    "end": end,
                    "magnitude_rad_s": round(_uniform(rng, profile_spec.imu_bias_range), 5),
                }
            )
        elif fault_type == "packet_loss":
            faults.append(
                {
                    "type": fault_type,
                    "start": start,
                    "end": end,
                    "rate": round(_uniform(rng, profile_spec.packet_loss_rate_range), 5),
                }
            )
        elif fault_type == "disturbance":
            faults.append(
                {
                    "type": fault_type,
                    "start": start,
                    "end": end,
                    "magnitude_rad": round(_uniform(rng, profile_spec.disturbance_range), 5),
                }
            )
        elif fault_type == "latency_spike":
            faults.append(
                {
                    "type": fault_type,
                    "start": start,
                    "end": end,
                    "seconds": round(_uniform(rng, profile_spec.latency_spike_range), 5),
                }
            )
        elif fault_type == "mode_churn":
            faults.append(
                {
                    "type": fault_type,
                    "start": start,
                    "end": end,
                    "period_s": round(rng.uniform(0.5, 3.0), 3),
                }
            )

    return {
        "seed": seed,
        "profile": profile,
        "duration_s": duration,
        "faults": faults,
    }

"""3-DoF point-mass trajectory simulator for property-based testing.

Models a Falcon-like launch vehicle with:
- 2D point-mass dynamics (downrange + altitude)
- Exponential atmosphere model with Mach-dependent drag
- Gravity turn pitch guidance with PID gimbal control
- Fault injection: IMU bias, packet loss, disturbance, latency, mode churn
- Abort logic with configurable triggers and delays
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from src.pbt.kalman import EKF, create_default_ekf

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
EARTH_GRAVITY = 9.80665  # m/s^2
SEA_LEVEL_DENSITY = 1.225  # kg/m^3
SCALE_HEIGHT = 8500.0  # m
SPEED_OF_SOUND_SEA = 343.0  # m/s at sea level

# ---------------------------------------------------------------------------
# Falcon-like vehicle defaults
# ---------------------------------------------------------------------------
INITIAL_MASS_KG = 550_000.0
DRY_MASS_KG = 30_000.0
THRUST_N = 7_600_000.0
BURN_TIME_S = 162.0
FUEL_FLOW_RATE = (INITIAL_MASS_KG - DRY_MASS_KG) / BURN_TIME_S
CD_SUBSONIC = 0.30
CD_SUPERSONIC = 0.45
REFERENCE_AREA_M2 = 10.04  # pi * (1.83m)^2


@dataclass(frozen=True)
class SimulationResult:
    trace: list[dict[str, Any]]


@dataclass
class _PID:
    """Simple PID controller with anti-windup clamping."""

    kp: float = 2.0
    ki: float = 0.1
    kd: float = 0.5
    integral: float = 0.0
    prev_error: float = 0.0
    output_limit: float = 0.2618  # ~15 deg default

    def step(self, error: float, dt: float) -> float:
        self.integral += error * dt
        self.integral = max(-1.0, min(1.0, self.integral))
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error
        raw = self.kp * error + self.ki * self.integral + self.kd * derivative
        return max(-self.output_limit, min(self.output_limit, raw))


@dataclass
class _VehicleState:
    """Mutable simulation state for the 2D trajectory."""

    x: float = 0.0  # downrange position (m)
    y: float = 0.0  # altitude (m)
    vx: float = 0.0  # downrange velocity (m/s)
    vy: float = 0.1  # vertical velocity (m/s) — small upward nudge off pad
    mass: float = INITIAL_MASS_KG
    pitch_rad: float = math.pi / 2.0  # pointing up at launch
    time_s: float = 0.0
    mode: str = "NOMINAL"
    abort_requested_at: float | None = None


# ---------------------------------------------------------------------------
# Atmosphere and aerodynamics
# ---------------------------------------------------------------------------

def _atmosphere(altitude_m: float) -> tuple[float, float]:
    """Return (density_kg_m3, speed_of_sound_m_s) at altitude."""
    h = max(0.0, altitude_m)
    density = SEA_LEVEL_DENSITY * math.exp(-h / SCALE_HEIGHT)
    temp_ratio = max(0.5, 1.0 - h / 44_330.0)
    speed_of_sound = SPEED_OF_SOUND_SEA * math.sqrt(temp_ratio)
    return density, speed_of_sound


def _drag_coefficient(mach: float) -> float:
    """Mach-dependent drag coefficient with transonic bump."""
    if mach < 0.8:
        return CD_SUBSONIC
    if mach < 1.2:
        return CD_SUBSONIC + (CD_SUPERSONIC - CD_SUBSONIC) * (mach - 0.8) / 0.4
    return CD_SUPERSONIC


# ---------------------------------------------------------------------------
# Guidance
# ---------------------------------------------------------------------------

def _pitch_program(time_s: float) -> float:
    """Gravity turn target pitch (rad from horizontal).

    Vertical for first 10 s, then linear kickover from 90 deg to 15 deg
    over the next 150 s.
    """
    if time_s < 10.0:
        return math.pi / 2.0
    progress = min(1.0, (time_s - 10.0) / 150.0)
    return math.pi / 2.0 - progress * math.radians(75.0)


# ---------------------------------------------------------------------------
# Fault helpers
# ---------------------------------------------------------------------------

def _fault_active(fault: dict[str, Any], t: float) -> bool:
    return float(fault.get("start", 0.0)) <= t <= float(fault.get("end", t))


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def run_scenario(
    compiled_config: dict[str, Any],
    scenario: dict[str, Any],
    dt: float = 0.1,
) -> SimulationResult:
    """Run a full trajectory simulation under the given scenario.

    Preserves the original trace contract (all fields that PBT-001..004 check)
    and adds 3-DoF fields for richer analysis.
    """
    config = (
        compiled_config["canonical_config"]
        if "canonical_config" in compiled_config
        else compiled_config
    )
    seed = int(scenario["seed"])
    rng = random.Random(seed)

    # Extract config parameters
    max_aoa = float(config["guidance"]["max_angle_of_attack"])
    max_gimbal_angle = float(config["control"]["actuator"]["max_gimbal_angle"])
    max_gimbal_rate = float(config["control"]["actuator"]["max_gimbal_rate"])
    packet_loss_budget = float(config["comms"]["packet_loss_budget"])
    imu_latency = float(config["navigation"]["imu"]["max_latency"])

    # Initialize state, controller, and Kalman filter
    state = _VehicleState()
    pid = _PID(output_limit=max_gimbal_angle)
    prev_gimbal = 0.0
    kf = create_default_ekf([0.0, 0.0, 0.0, 0.1, 0.0])
    step_count = 0

    duration_s = float(scenario["duration_s"])
    faults = list(scenario.get("faults", []))
    trace: list[dict[str, Any]] = []

    while state.time_s <= duration_s + 1e-9:
        t = round(state.time_s, 6)

        # ------------------------------------------------------------------
        # Fault injection
        # ------------------------------------------------------------------
        packet_loss = 0.0
        imu_bias = 0.0
        disturbance_force = 0.0
        extra_latency = 0.0
        mode_churn = False

        for fault in faults:
            if not _fault_active(fault, t):
                continue
            ft = fault["type"]
            if ft == "packet_loss":
                packet_loss = max(packet_loss, float(fault.get("rate", 0.0)))
            elif ft == "imu_bias":
                imu_bias += float(fault.get("magnitude_rad_s", 0.0))
            elif ft == "disturbance":
                mag = float(fault.get("magnitude_rad", 0.0))
                disturbance_force += mag * THRUST_N * 0.05
            elif ft == "latency_spike":
                extra_latency = max(extra_latency, float(fault.get("seconds", 0.0)))
            elif ft == "mode_churn":
                period_s = max(0.2, float(fault.get("period_s", 1.0)))
                mode_churn = int(t / period_s) % 2 == 0

        # ------------------------------------------------------------------
        # Aerodynamics
        # ------------------------------------------------------------------
        speed = math.sqrt(state.vx ** 2 + state.vy ** 2)
        density, sound_speed = _atmosphere(state.y)
        mach = speed / sound_speed if sound_speed > 0 else 0.0
        cd = _drag_coefficient(mach)
        dynamic_pressure = 0.5 * density * speed * speed
        drag = dynamic_pressure * cd * REFERENCE_AREA_M2

        # ------------------------------------------------------------------
        # Flight path angle and AoA
        # ------------------------------------------------------------------
        fpa = math.atan2(state.vy, max(1e-6, abs(state.vx)))
        true_aoa = state.pitch_rad - fpa

        # ------------------------------------------------------------------
        # Kalman filter: predict + sensor fusion
        # ------------------------------------------------------------------
        kf.predict(ax=0.0, ay=0.0, aoa_rate=0.0, dt=dt)

        # IMU measurement (high rate): corrupted by bias + noise
        imu_vx = state.vx + imu_bias * dt * 10.0 + rng.gauss(0, 0.3)
        imu_vy = state.vy + imu_bias * dt * 10.0 + rng.gauss(0, 0.3)
        imu_aoa = true_aoa + imu_bias * dt + rng.gauss(0, 0.005)
        kf.update_imu(imu_vx, imu_vy, imu_aoa)

        # GPS measurement (low rate: every 10th step ≈ 1 Hz)
        if step_count % 10 == 0:
            gps_x = state.x + rng.gauss(0, 2.0)
            gps_y = state.y + rng.gauss(0, 2.0)
            kf.update_gps(gps_x, gps_y)

        estimated_aoa = kf.x_hat[4]
        estimation_error = abs(true_aoa - estimated_aoa)
        kf_innovation_norm = sum(abs(v) for v in kf.innovation)

        # ------------------------------------------------------------------
        # Guidance and control (uses KF-estimated AoA)
        # ------------------------------------------------------------------
        target_pitch = _pitch_program(t)
        pitch_error = target_pitch - state.pitch_rad
        gimbal_command = pid.step(-estimated_aoa + pitch_error * 0.5, dt)

        # Rate-limit the gimbal
        max_delta = max_gimbal_rate * dt
        gimbal_delta = gimbal_command - prev_gimbal
        gimbal_delta = max(-max_delta, min(max_delta, gimbal_delta))
        gimbal_command = prev_gimbal + gimbal_delta
        gimbal_command = max(-max_gimbal_angle, min(max_gimbal_angle, gimbal_command))
        prev_gimbal = gimbal_command

        # ------------------------------------------------------------------
        # Abort logic
        # ------------------------------------------------------------------
        abort_trigger = (
            abs(true_aoa) > max_aoa
            or packet_loss > packet_loss_budget * 1.2
            or mode_churn
        )
        if abort_trigger and state.abort_requested_at is None:
            state.abort_requested_at = t

        if state.abort_requested_at is not None and state.mode == "NOMINAL":
            abort_delay = 0.6 + imu_latency + extra_latency
            if t - float(state.abort_requested_at) >= abort_delay:
                state.mode = "ABORT"

        # ------------------------------------------------------------------
        # Forces and integration
        # ------------------------------------------------------------------
        thrust_active = state.mass > DRY_MASS_KG and state.mode != "ABORT"
        thrust = THRUST_N if thrust_active else 0.0

        effective_pitch = state.pitch_rad + gimbal_command

        # Gravity
        fx = 0.0
        fy = -EARTH_GRAVITY * state.mass

        # Thrust
        if thrust > 0:
            fx += thrust * math.cos(effective_pitch)
            fy += thrust * math.sin(effective_pitch)

        # Drag (opposes velocity)
        if speed > 1e-6:
            fx -= drag * (state.vx / speed)
            fy -= drag * (state.vy / speed)

        # Disturbance + random perturbation (lateral)
        fx += disturbance_force + rng.uniform(-500.0, 500.0)

        # Abort damping — reduce all forces to let vehicle coast
        if state.mode == "ABORT":
            fx *= 0.5
            fy *= 0.5

        # Accelerations
        ax = fx / state.mass
        ay = fy / state.mass
        accel_magnitude = math.sqrt(ax ** 2 + ay ** 2)

        # Euler integration
        state.vx += ax * dt
        state.vy += ay * dt
        state.x += state.vx * dt
        state.y = max(0.0, state.y + state.vy * dt)

        # Mass depletion
        if thrust_active:
            state.mass = max(DRY_MASS_KG, state.mass - FUEL_FLOW_RATE * dt)

        # Pitch update: follows flight path angle + gimbal authority
        new_fpa = math.atan2(state.vy, max(1e-6, abs(state.vx)))
        pitch_rate = (new_fpa - fpa) / dt if dt > 0 else 0.0
        state.pitch_rad += pitch_rate * dt + gimbal_command * 0.3 * dt

        # Abort AoA damping — drive pitch toward flight path angle
        if state.mode == "ABORT":
            true_aoa_now = state.pitch_rad - new_fpa
            state.pitch_rad -= true_aoa_now * 0.03

        # ------------------------------------------------------------------
        # Record trace
        # ------------------------------------------------------------------
        is_finite = math.isfinite(gimbal_command) and math.isfinite(true_aoa)
        trace.append(
            {
                # Original trace contract (PBT-001..004 depend on these)
                "time_s": t,
                "mode": state.mode,
                "aoa_rad": true_aoa,
                "max_aoa_rad": max_aoa,
                "command_rad": gimbal_command,
                "packet_loss": packet_loss,
                "abort_requested": state.abort_requested_at is not None,
                "abort_requested_at": state.abort_requested_at,
                "is_finite": is_finite,
                # 3-DoF fields
                "altitude_m": state.y,
                "velocity_m_s": speed,
                "acceleration_g": accel_magnitude / EARTH_GRAVITY,
                "dynamic_pressure_Pa": dynamic_pressure,
                "mach": mach,
                "thrust_N": thrust,
                "mass_kg": state.mass,
                "pitch_rad": state.pitch_rad,
                "flight_path_angle_rad": fpa,
                # Kalman filter fields
                "estimated_aoa_rad": estimated_aoa,
                "estimation_error_rad": estimation_error,
                "kf_innovation": kf_innovation_norm,
            }
        )

        step_count += 1
        state.time_s += dt

    return SimulationResult(trace=trace)

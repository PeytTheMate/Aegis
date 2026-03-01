"""Trace visualization for PBT failure bundles.

Renders simulation traces as publication-quality PNG figures using
matplotlib. Falls back gracefully with a clear error message if
matplotlib is not installed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _load_trace(bundle_dir: Path) -> list[dict[str, Any]]:
    with (bundle_dir / "trace.csv").open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_scenario(bundle_dir: Path) -> dict[str, Any]:
    return json.loads((bundle_dir / "scenario.json").read_text(encoding="utf-8"))


def plot_trace(bundle_dir: str | Path, output: str | Path | None = None) -> Path:
    """Render a failure trace as a PNG figure.

    Returns the path to the saved image.
    Raises ImportError if matplotlib is not installed.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. "
            "Install with: pip install 'mission-toolchain[plot]'"
        ) from None

    bundle_path = Path(bundle_dir)
    trace = _load_trace(bundle_path)
    scenario = _load_scenario(bundle_path)

    times = [float(r["time_s"]) for r in trace]
    aoas = [float(r["aoa_rad"]) for r in trace]
    max_aoa = float(trace[0]["max_aoa_rad"])
    commands = [float(r["command_rad"]) for r in trace]
    modes = [r["mode"] for r in trace]

    has_3dof = "altitude_m" in trace[0]

    if has_3dof:
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        ax_aoa = axes[0, 0]
        ax_alt = axes[0, 1]
        ax_dyn = axes[1, 0]
        ax_mach = axes[1, 1]
    else:
        fig, ax_aoa = plt.subplots(1, 1, figsize=(14, 6))

    # ------------------------------------------------------------------
    # Panel 1: AoA + command + mode regions + fault windows
    # ------------------------------------------------------------------
    mode_colors = {"NOMINAL": "#d4edda", "ABORT_PENDING": "#fff3cd", "ABORT": "#f8d7da"}
    prev_mode = modes[0]
    region_start = times[0]
    for i in range(1, len(times)):
        if modes[i] != prev_mode or i == len(times) - 1:
            ax_aoa.axvspan(
                region_start, times[i], alpha=0.3,
                color=mode_colors.get(prev_mode, "#eeeeee"), zorder=0,
            )
            region_start = times[i]
            prev_mode = modes[i]

    for fault in scenario.get("faults", []):
        ax_aoa.axvspan(
            float(fault["start"]), float(fault["end"]),
            alpha=0.08, color="purple", hatch="//", zorder=0,
        )

    ax_aoa.plot(times, aoas, "b-", linewidth=1.2, label="AoA (rad)")
    ax_aoa.axhline(y=max_aoa, color="r", linestyle="--", linewidth=1.0, label=f"max AoA ({max_aoa:.3f} rad)")
    ax_aoa.axhline(y=-max_aoa, color="r", linestyle="--", linewidth=1.0)

    if "estimated_aoa_rad" in trace[0]:
        est_aoas = [float(r["estimated_aoa_rad"]) for r in trace]
        ax_aoa.plot(times, est_aoas, "c--", linewidth=0.8, alpha=0.7, label="KF estimate")

    ax_aoa.set_xlabel("Time (s)")
    ax_aoa.set_ylabel("Angle of Attack (rad)", color="b")
    ax_aoa.tick_params(axis="y", labelcolor="b")

    ax_cmd = ax_aoa.twinx()
    ax_cmd.plot(times, commands, "g-", linewidth=0.8, alpha=0.5, label="Command (rad)")
    ax_cmd.set_ylabel("Gimbal Command (rad)", color="g")
    ax_cmd.tick_params(axis="y", labelcolor="g")

    mode_patches = [mpatches.Patch(color=c, alpha=0.3, label=m) for m, c in mode_colors.items()]
    fault_patch = mpatches.Patch(facecolor="purple", alpha=0.1, hatch="//", label="Fault window")
    h1, l1 = ax_aoa.get_legend_handles_labels()
    h2, l2 = ax_cmd.get_legend_handles_labels()
    ax_aoa.legend(
        handles=h1 + h2 + mode_patches + [fault_patch],
        labels=l1 + l2 + list(mode_colors.keys()) + ["Fault window"],
        loc="upper right", fontsize=7,
    )
    ax_aoa.set_title("Angle of Attack & Gimbal Command")

    # ------------------------------------------------------------------
    # 3-DoF panels (if available)
    # ------------------------------------------------------------------
    if has_3dof:
        altitudes = [float(r["altitude_m"]) for r in trace]
        dyn_pressures = [float(r["dynamic_pressure_Pa"]) for r in trace]
        machs = [float(r["mach"]) for r in trace]

        # Panel 2: Altitude
        ax_alt.plot(times, [a / 1000.0 for a in altitudes], "k-", linewidth=1.2)
        ax_alt.set_xlabel("Time (s)")
        ax_alt.set_ylabel("Altitude (km)")
        ax_alt.set_title("Altitude Profile")
        ax_alt.grid(True, alpha=0.3)

        # Panel 3: Dynamic pressure
        ax_dyn.plot(times, [q / 1000.0 for q in dyn_pressures], "m-", linewidth=1.2)
        max_q_idx = dyn_pressures.index(max(dyn_pressures))
        ax_dyn.axvline(x=times[max_q_idx], color="r", linestyle=":", alpha=0.6)
        ax_dyn.annotate(
            f"Max-Q: {max(dyn_pressures)/1000:.1f} kPa",
            xy=(times[max_q_idx], max(dyn_pressures) / 1000.0),
            xytext=(10, -15), textcoords="offset points", fontsize=8,
            arrowprops=dict(arrowstyle="->", color="red", lw=0.8),
        )
        ax_dyn.set_xlabel("Time (s)")
        ax_dyn.set_ylabel("Dynamic Pressure (kPa)")
        ax_dyn.set_title("Dynamic Pressure (Max-Q)")
        ax_dyn.grid(True, alpha=0.3)

        # Panel 4: Mach number
        ax_mach.plot(times, machs, color="darkorange", linewidth=1.2)
        ax_mach.axhline(y=1.0, color="gray", linestyle="--", alpha=0.5, label="Mach 1")
        ax_mach.set_xlabel("Time (s)")
        ax_mach.set_ylabel("Mach Number")
        ax_mach.set_title("Mach Number")
        ax_mach.legend(fontsize=8)
        ax_mach.grid(True, alpha=0.3)

    seed = scenario.get("seed", "?")
    profile = scenario.get("profile", "?")
    fig.suptitle(
        f"PBT Failure Trace \u2014 Seed {seed}, Profile: {profile}",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout()

    if output is None:
        output = bundle_path / "trace_plot.png"
    output_path = Path(output)
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close(fig)

    return output_path

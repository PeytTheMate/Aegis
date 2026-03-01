"""PBT run, replay, and shrink orchestration."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from src.pbt.bundles import load_bundle, write_failure_bundle
from src.pbt.generator import generate_scenario
from src.pbt.properties import evaluate_properties
from src.pbt.shrinker import shrink_scenario
from src.pbt.sut import run_scenario



def _run_once(compiled_artifact: dict[str, Any], scenario: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    simulation = run_scenario(compiled_artifact, scenario)
    config = compiled_artifact["canonical_config"] if "canonical_config" in compiled_artifact else compiled_artifact
    violations = evaluate_properties(simulation.trace, config)
    return simulation.trace, violations



def _run_single_scenario(args: tuple[dict[str, Any], int, str]) -> dict[str, Any]:
    """Run a single scenario. Top-level function for multiprocessing pickling."""
    compiled_artifact, seed, profile = args
    scenario = generate_scenario(seed=seed, profile=profile)
    trace, violations = _run_once(compiled_artifact, scenario)
    return {
        "seed": seed,
        "scenario": scenario,
        "trace": trace,
        "violations": violations,
        "passed": not violations,
    }



def run_property_tests(
    compiled_artifact: dict[str, Any],
    runs: int,
    profile: str,
    failure_root: str | Path = "failures",
    base_seed: int = 1337,
    workers: int = 1,
    benchmark: bool = False,
) -> dict[str, Any]:
    start_time = time.monotonic()

    seeds = [base_seed + offset for offset in range(runs)]
    args_list = [(compiled_artifact, seed, profile) for seed in seeds]

    if workers > 1:
        from multiprocessing import Pool
        with Pool(processes=workers) as pool:
            raw_results = pool.map(_run_single_scenario, args_list)
    else:
        raw_results = [_run_single_scenario(a) for a in args_list]

    # Post-process: shrink failures and write bundles (sequential)
    failures: list[str] = []
    run_results: list[dict[str, Any]] = []

    def scenario_fails(candidate: dict[str, Any]) -> bool:
        _, candidate_violations = _run_once(compiled_artifact, candidate)
        return bool(candidate_violations)

    for raw in raw_results:
        record: dict[str, Any] = {
            "seed": raw["seed"],
            "passed": raw["passed"],
            "violations": raw["violations"],
        }

        if not raw["passed"]:
            minimized = shrink_scenario(raw["scenario"], scenario_fails)
            minimized_trace, minimized_violations = _run_once(compiled_artifact, minimized)
            bundle = write_failure_bundle(
                failure_root, compiled_artifact, minimized,
                minimized_trace, minimized_violations,
            )
            failures.append(str(bundle))
            record["bundle"] = str(bundle)
            record["original_fault_count"] = len(raw["scenario"].get("faults", []))
            record["shrunk_fault_count"] = len(minimized.get("faults", []))
            record["original_duration_s"] = raw["scenario"].get("duration_s")
            record["shrunk_duration_s"] = minimized.get("duration_s")

        run_results.append(record)

    elapsed = time.monotonic() - start_time
    summary: dict[str, Any] = {
        "runs": runs,
        "profile": profile,
        "failures": failures,
        "failure_count": len(failures),
        "results": run_results,
    }

    if benchmark:
        summary["benchmark"] = {
            "wall_clock_s": round(elapsed, 3),
            "scenarios_per_second": round(runs / elapsed, 1) if elapsed > 0 else 0,
            "workers": workers,
        }

    return summary



def replay_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    payload = load_bundle(bundle_dir)
    trace, violations = _run_once(payload["compiled"], payload["scenario"])
    return {
        "bundle": str(bundle_dir),
        "violations": violations,
        "passed": not violations,
        "trace_steps": len(trace),
    }



def shrink_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    payload = load_bundle(bundle_dir)
    compiled = payload["compiled"]
    scenario = payload["scenario"]

    def scenario_fails(candidate: dict[str, Any]) -> bool:
        _, violations = _run_once(compiled, candidate)
        return bool(violations)

    minimized = shrink_scenario(scenario, scenario_fails)
    trace, violations = _run_once(compiled, minimized)

    from src.common.io_utils import write_json

    root = Path(bundle_dir)
    write_json(root / "scenario_shrunk.json", minimized)

    report = ["# Shrink Report", "", f"- Original duration: {scenario.get('duration_s')}", f"- Shrunk duration: {minimized.get('duration_s')}", f"- Original faults: {len(scenario.get('faults', []))}", f"- Shrunk faults: {len(minimized.get('faults', []))}", "", "## Violations"]
    for violation in violations:
        report.append(f"- {violation['property_id']}: {violation['message']}")
    (root / "shrink_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    return {
        "bundle": str(bundle_dir),
        "shrunk_scenario": minimized,
        "violations": violations,
        "trace_steps": len(trace),
    }

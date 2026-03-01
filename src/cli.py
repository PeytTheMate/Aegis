"""CLI entrypoints for MCV, PBT, pipeline, and assurance workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.assurance.formal_mode_logic import render_formal_markdown, verify_mode_logic
from src.assurance.safety_case import build_safety_report, render_safety_markdown
from src.assurance.traceability import (
    build_traceability_report,
    write_traceability_outputs,
)
from src.common.io_utils import write_json
from src.mcv.diagnostics import format_diagnostic_text
from src.mcv.service import compile_file, diff_files, explain_file, load_compiled, validate_file
from src.pbt.runner import replay_bundle, run_property_tests, shrink_bundle



def _print_payload(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))



def _handle_mcv_validate(args: argparse.Namespace) -> int:
    result = validate_file(args.mission)
    if args.json:
        _print_payload(
            {
                "valid": result.valid,
                "diagnostics": [diag.as_dict() for diag in result.diagnostics],
            }
        )
    else:
        if result.valid:
            print("Mission config is valid.")
        else:
            for diagnostic in result.diagnostics:
                print(format_diagnostic_text(diagnostic, result.source))
                print()
    return 0 if result.valid else 1



def _handle_mcv_compile(args: argparse.Namespace) -> int:
    validation, compiled = compile_file(args.mission, args.output)
    if not validation.valid:
        for diagnostic in validation.diagnostics:
            print(format_diagnostic_text(diagnostic, validation.source))
            print()
        return 1

    assert compiled is not None
    if args.output is None:
        _print_payload(compiled.artifact)
    else:
        print(f"Compiled artifact written to {args.output}")
    return 0



def _handle_mcv_diff(args: argparse.Namespace) -> int:
    result_a, result_b, diff = diff_files(args.a, args.b)
    if not result_a.valid or not result_b.valid:
        print("Both mission files must validate before semantic diffing.")
        for result in (result_a, result_b):
            for diagnostic in result.diagnostics:
                print(format_diagnostic_text(diagnostic, result.source))
                print()
        return 1

    if args.json:
        _print_payload({"differences": diff})
    else:
        if not diff:
            print("No semantic differences.")
        for entry in diff:
            print(f"{entry['path']}: {entry['a']} -> {entry['b']}")
    return 0



def _handle_mcv_explain(args: argparse.Namespace) -> int:
    result = explain_file(args.mission).validation
    payload = {
        "valid": result.valid,
        "diagnostics": [diag.as_dict() for diag in result.diagnostics],
        "normalized_config": result.normalized_config if result.valid else None,
    }
    if args.json:
        _print_payload(payload)
    else:
        if result.valid:
            print("Mission config is valid and explain has no errors.")
        else:
            for diagnostic in result.diagnostics:
                print(format_diagnostic_text(diagnostic, result.source))
                print()
    return 0 if result.valid else 1



def _handle_pbt_plot(args: argparse.Namespace) -> int:
    try:
        from src.pbt.plotting import plot_trace
    except ImportError as exc:
        print(f"Error: {exc}")
        return 1
    output = plot_trace(args.bundle, args.output)
    print(f"Plot saved to {output}")
    return 0



def _handle_pbt_run(args: argparse.Namespace) -> int:
    compiled = load_compiled(args.compiled)
    summary = run_property_tests(
        compiled_artifact=compiled,
        runs=args.runs,
        profile=args.profile,
        failure_root=args.failure_root,
        base_seed=args.seed,
        workers=args.workers,
        benchmark=args.benchmark,
    )

    if args.output:
        write_json(args.output, summary)
        print(f"PBT summary written to {args.output}")
    else:
        _print_payload(summary)

    return 0 if summary["failure_count"] == 0 else 2



def _handle_pbt_replay(args: argparse.Namespace) -> int:
    summary = replay_bundle(args.bundle)
    _print_payload(summary)
    return 0 if summary["passed"] else 2



def _handle_pbt_shrink(args: argparse.Namespace) -> int:
    summary = shrink_bundle(args.bundle)
    _print_payload(summary)
    return 0 if summary["violations"] else 1



def _handle_pipeline_run(args: argparse.Namespace) -> int:
    output = args.compiled_output or Path(".artifacts") / "compiled.json"
    validation, compiled = compile_file(args.mission, output)
    if not validation.valid:
        for diagnostic in validation.diagnostics:
            print(format_diagnostic_text(diagnostic, validation.source))
            print()
        return 1

    assert compiled is not None
    summary = run_property_tests(
        compiled_artifact=compiled.artifact,
        runs=args.runs,
        profile=args.profile,
        failure_root=args.failure_root,
        base_seed=args.seed,
        workers=args.workers,
        benchmark=args.benchmark,
    )
    _print_payload(
        {
            "compiled_artifact": str(output),
            "pbt": summary,
        }
    )
    return 0 if summary["failure_count"] == 0 else 2



def _handle_assurance_traceability(args: argparse.Namespace) -> int:
    report = build_traceability_report(args.requirements)
    if args.output_json or args.output_markdown:
        output_json = args.output_json or Path(".artifacts") / "assurance" / "traceability_report.json"
        output_markdown = args.output_markdown or Path(".artifacts") / "assurance" / "traceability_report.md"
        write_traceability_outputs(report, output_json, output_markdown)
        print(f"Traceability reports written to {output_json} and {output_markdown}")
    else:
        _print_payload(report)
    return 0 if report["passed"] else 3



def _handle_assurance_safety(args: argparse.Namespace) -> int:
    report = build_safety_report(args.requirements, args.hazards, args.safety_case)
    if args.output_json or args.output_markdown:
        output_json = args.output_json or Path(".artifacts") / "assurance" / "safety_report.json"
        output_markdown = args.output_markdown or Path(".artifacts") / "assurance" / "safety_report.md"
        write_json(output_json, report)
        Path(output_markdown).write_text(render_safety_markdown(report), encoding="utf-8")
        print(f"Safety reports written to {output_json} and {output_markdown}")
    else:
        _print_payload(report)
    return 0 if report["passed"] else 3



def _handle_assurance_formal(args: argparse.Namespace) -> int:
    report = verify_mode_logic(
        horizon_steps=args.horizon_steps,
        abort_delay_steps=args.abort_delay_steps,
        abort_deadline_steps=args.abort_deadline_steps,
        assume_imu_healthy=not args.allow_imu_unhealthy,
        allow_abort_exit=args.allow_abort_exit,
    )
    if args.output_json or args.output_markdown:
        output_json = args.output_json or Path(".artifacts") / "assurance" / "formal_report.json"
        output_markdown = args.output_markdown or Path(".artifacts") / "assurance" / "formal_report.md"
        write_json(output_json, report)
        Path(output_markdown).write_text(render_formal_markdown(report), encoding="utf-8")
        print(f"Formal reports written to {output_json} and {output_markdown}")
    else:
        _print_payload(report)
    return 0 if report["passed"] else 3



def _handle_assurance_check(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    traceability = build_traceability_report(args.requirements)
    write_traceability_outputs(
        traceability,
        output_dir / "traceability_report.json",
        output_dir / "traceability_report.md",
    )

    safety = build_safety_report(args.requirements, args.hazards, args.safety_case)
    write_json(output_dir / "safety_report.json", safety)
    (output_dir / "safety_report.md").write_text(render_safety_markdown(safety), encoding="utf-8")

    formal = verify_mode_logic(
        horizon_steps=args.horizon_steps,
        abort_delay_steps=args.abort_delay_steps,
        abort_deadline_steps=args.abort_deadline_steps,
        assume_imu_healthy=True,
        allow_abort_exit=False,
    )
    write_json(output_dir / "formal_report.json", formal)
    (output_dir / "formal_report.md").write_text(render_formal_markdown(formal), encoding="utf-8")

    summary = {
        "traceability_passed": traceability["passed"],
        "safety_passed": safety["passed"],
        "formal_passed": formal["passed"],
        "output_dir": str(output_dir),
    }
    _print_payload(summary)
    return 0 if all(summary[key] for key in ("traceability_passed", "safety_passed", "formal_passed")) else 3



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mission configuration and property testing toolchain")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mcv_parser = subparsers.add_parser("mcv", help="Mission configuration verifier")
    mcv_sub = mcv_parser.add_subparsers(dest="mcv_command", required=True)

    validate_parser = mcv_sub.add_parser("validate", help="Validate a mission file")
    validate_parser.add_argument("mission")
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.set_defaults(func=_handle_mcv_validate)

    compile_parser = mcv_sub.add_parser("compile", help="Compile a mission config")
    compile_parser.add_argument("mission")
    compile_parser.add_argument("-o", "--output")
    compile_parser.set_defaults(func=_handle_mcv_compile)

    diff_parser = mcv_sub.add_parser("diff", help="Semantic diff between mission files")
    diff_parser.add_argument("a")
    diff_parser.add_argument("b")
    diff_parser.add_argument("--json", action="store_true")
    diff_parser.set_defaults(func=_handle_mcv_diff)

    explain_parser = mcv_sub.add_parser("explain", help="Explain mission validation results")
    explain_parser.add_argument("mission")
    explain_parser.add_argument("--json", action="store_true")
    explain_parser.set_defaults(func=_handle_mcv_explain)

    pbt_parser = subparsers.add_parser("pbt", help="Property-based testing harness")
    pbt_sub = pbt_parser.add_subparsers(dest="pbt_command", required=True)

    run_parser = pbt_sub.add_parser("run", help="Run randomized scenarios")
    run_parser.add_argument("compiled")
    run_parser.add_argument("--runs", type=int, default=100)
    run_parser.add_argument("--profile", default="nominal")
    run_parser.add_argument("--failure-root", default="failures")
    run_parser.add_argument("--seed", type=int, default=1337)
    run_parser.add_argument("--output")
    run_parser.add_argument("--workers", type=int, default=1, help="Parallel workers (default: 1)")
    run_parser.add_argument("--benchmark", action="store_true", help="Report timing statistics")
    run_parser.set_defaults(func=_handle_pbt_run)

    replay_parser = pbt_sub.add_parser("replay", help="Replay a failure bundle")
    replay_parser.add_argument("bundle")
    replay_parser.set_defaults(func=_handle_pbt_replay)

    shrink_parser = pbt_sub.add_parser("shrink", help="Shrink a failure bundle scenario")
    shrink_parser.add_argument("bundle")
    shrink_parser.set_defaults(func=_handle_pbt_shrink)

    plot_parser = pbt_sub.add_parser("plot", help="Visualize a failure trace")
    plot_parser.add_argument("bundle", help="Path to failure bundle directory")
    plot_parser.add_argument("-o", "--output", help="Output PNG path")
    plot_parser.set_defaults(func=_handle_pbt_plot)

    pipeline_parser = subparsers.add_parser("pipeline", help="End-to-end MCV + PBT")
    pipeline_sub = pipeline_parser.add_subparsers(dest="pipeline_command", required=True)

    pipeline_run_parser = pipeline_sub.add_parser("run", help="Validate, compile, and run PBT")
    pipeline_run_parser.add_argument("mission")
    pipeline_run_parser.add_argument("--runs", type=int, default=100)
    pipeline_run_parser.add_argument("--profile", default="nominal")
    pipeline_run_parser.add_argument("--seed", type=int, default=1337)
    pipeline_run_parser.add_argument("--failure-root", default="failures")
    pipeline_run_parser.add_argument("--compiled-output")
    pipeline_run_parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    pipeline_run_parser.add_argument("--benchmark", action="store_true", help="Report timing statistics")
    pipeline_run_parser.set_defaults(func=_handle_pipeline_run)

    assurance_parser = subparsers.add_parser("assurance", help="Requirements, safety-case, and formal checks")
    assurance_sub = assurance_parser.add_subparsers(dest="assurance_command", required=True)

    traceability_parser = assurance_sub.add_parser("traceability-report", help="Generate requirements traceability report")
    traceability_parser.add_argument("--requirements")
    traceability_parser.add_argument("--output-json")
    traceability_parser.add_argument("--output-markdown")
    traceability_parser.set_defaults(func=_handle_assurance_traceability)

    safety_parser = assurance_sub.add_parser("safety-report", help="Validate hazard log and safety case links")
    safety_parser.add_argument("--requirements")
    safety_parser.add_argument("--hazards")
    safety_parser.add_argument("--safety-case")
    safety_parser.add_argument("--output-json")
    safety_parser.add_argument("--output-markdown")
    safety_parser.set_defaults(func=_handle_assurance_safety)

    formal_parser = assurance_sub.add_parser("formal-verify", help="Run executable mode-logic model checking")
    formal_parser.add_argument("--horizon-steps", type=int, default=8)
    formal_parser.add_argument("--abort-delay-steps", type=int, default=3)
    formal_parser.add_argument("--abort-deadline-steps", type=int, default=4)
    formal_parser.add_argument("--allow-imu-unhealthy", action="store_true")
    formal_parser.add_argument("--allow-abort-exit", action="store_true")
    formal_parser.add_argument("--output-json")
    formal_parser.add_argument("--output-markdown")
    formal_parser.set_defaults(func=_handle_assurance_formal)

    check_parser = assurance_sub.add_parser("check", help="Run traceability, safety, and formal checks together")
    check_parser.add_argument("--requirements")
    check_parser.add_argument("--hazards")
    check_parser.add_argument("--safety-case")
    check_parser.add_argument("--output-dir", default=".artifacts/assurance")
    check_parser.add_argument("--horizon-steps", type=int, default=8)
    check_parser.add_argument("--abort-delay-steps", type=int, default=3)
    check_parser.add_argument("--abort-deadline-steps", type=int, default=4)
    check_parser.set_defaults(func=_handle_assurance_check)

    return parser



def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

# Phased Implementation Log

## Phase 0: Repo + CLI Skeleton

- Scaffolded repository structure with `src/mcv`, `src/pbt`, `src/common`, `configs`, `tests`, `docs`, `scripts`, and CI workflow.
- Added unified CLI in `src/cli.py` with `mcv`, `pbt`, and `pipeline` command groups.

## Phase 1: Parsing + Typing + Units

- Implemented YAML/JSON loading and custom YAML subset parser.
- Added deterministic default injection and schema-driven type checks.
- Added unit normalization to base units (rad, s, Pa, rad/s).

## Phase 2: Constraint Engine + Diagnostics

- Implemented cross-field constraint rules (dependencies, ranges, sensor availability, safe envelopes).
- Added structured diagnostics with rule IDs, paths, explanations, suggestions, and JSON output.

## Phase 3: Compiled Artifacts + Diffing

- Added compiled artifact generation with canonical config, schema/config hashes, tool version, and timestamp.
- Added semantic diff over normalized configs with floating-point tolerance.

## Phase 4: Scenario Generation + Toy SUT

- Added deterministic scenario generator with profile-based adversarial distributions.
- Implemented toy flight-like SUT with state/mode dynamics and fault effects.

## Phase 5: Property Checks + Failure Bundles

- Added invariant/property checks for AoA bounds, abort liveness, non-finite outputs, and mode transitions.
- Added failure bundles with scenario, trace CSV, report, compiled artifact, and replay script.

## Phase 6: Shrinking + Replay

- Implemented scenario shrinking: duration reduction, fault removal, magnitude reduction.
- Added replay and shrink CLI commands for deterministic counterexample workflows.

## Phase 7: Case Studies + Docs

- Added architecture docs and required case studies.
- Added full test suite covering MCV, PBT, and integration pipeline behavior.

## Post-Phase Assurance Additions

- Added requirements-to-evidence traceability with machine-readable and markdown reports.
- Added hazard log and safety-case linkage validation.
- Added executable formal verification for mode-logic invariants with counterexample support.

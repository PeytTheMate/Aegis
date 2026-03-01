# Architecture Notes

## Layer 1: MCV

- Input: YAML (primary) and JSON mission config.
- Parse: custom YAML subset parser to avoid external dependencies.
- Type-check + units:
  - AoA: `deg|rad -> rad`
  - Latency/skew: `ms|s -> s`
  - Gimbal rates: `deg/s|rad/s -> rad/s`
- Deterministic defaults are merged before validation.
- Constraints are pure functions that emit diagnostics with:
  - rule id
  - severity
  - field path
  - explanation
  - optional suggestion

## Layer 2: PBT

- Input: compiled artifact with canonical config.
- Scenario generation: deterministic by seed with profile-based distributions.
- Toy SUT: flight-like mode/state + control loop + fault handling.
- Property library checks:
  - AoA safety bound
  - abort liveness (enter ABORT within 2s)
  - no NaN/non-finite outputs
  - state transition validity
- Failures create replayable bundles with scenario, trace, report, and repro script.
- Shrinker minimizes duration, fault count, and fault magnitudes while preserving failure.

## Determinism

- Scenario generation and simulation use seeded RNG.
- Failure bundles contain everything required for replay.

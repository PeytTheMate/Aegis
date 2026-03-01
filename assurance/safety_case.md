# Safety Case (Lightweight)

## Top Claim

`SC-000`: Mission toolchain reduces preflight and runtime control risk to acceptable simulation level.

## Claim Structure

- `SC-100`: Invalid configurations are rejected before runtime execution.
- `SC-200`: Runtime randomized testing detects safety and liveness failures with replayable evidence.
- `SC-300`: Mode logic invariants are formally verified against an executable transition model.

## Hazard Coverage

- `HZ-001` mapped to `REQ-PBT-001`, `REQ-MCV-003`.
- `HZ-002` mapped to `REQ-MCV-002`, `REQ-PBT-002`.
- `HZ-003` mapped to `REQ-SM-001`, `REQ-SM-002`.
- `HZ-004` mapped to `REQ-PBT-003`.

## Evidence Pointers

- Requirements traceability report: `.artifacts/assurance/traceability_report.json` and `.artifacts/assurance/traceability_report.md`.
- Safety consistency report: `.artifacts/assurance/safety_report.json` and `.artifacts/assurance/safety_report.md`.
- Formal mode report: `.artifacts/assurance/formal_report.json` and `.artifacts/assurance/formal_report.md`.

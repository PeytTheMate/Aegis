# Traceability Report

- Generated: 2026-02-28T23:27:45Z
- Requirements total: 9
- Requirements with issues: 0
- Issues total: 0

## Requirement Matrix

| Requirement | Constraints | Properties | Formal | Tests | Artifacts | Status |
|---|---|---|---|---|---|---|
| REQ-MCV-001 | MCV-014 | - | - | tests/mcv/test_mcv_constraints.py::TestMCVConstraints.test_invalid_autonomous_abort | compiled_artifact | ok |
| REQ-MCV-002 | MCV-016, MCV-017 | - | - | tests/mcv/test_mcv_constraints.py::TestMCVConstraints.test_invalid_autonomous_abort | validation_diagnostics | ok |
| REQ-MCV-003 | MCV-015 | - | - | tests/mcv/test_mcv_validation.py::TestMCVValidation.test_defaults_injected_deterministically | compiled_artifact | ok |
| REQ-PBT-001 | - | PBT-001 | - | tests/pbt/test_runner_bundle_and_shrink.py::TestRunnerBundleAndShrink.test_failure_bundle_and_replay | failure_bundle, trace_csv | ok |
| REQ-PBT-002 | - | PBT-002 | FML-003 | tests/pbt/test_runner_bundle_and_shrink.py::TestRunnerBundleAndShrink.test_failure_bundle_and_replay, tests/assurance/test_formal_mode_logic.py::TestFormalModeLogic.test_formal_checker_passes_default_model | failure_bundle, formal_report | ok |
| REQ-PBT-003 | - | PBT-003 | - | tests/pbt/test_runner_bundle_and_shrink.py::TestRunnerBundleAndShrink.test_failure_bundle_and_replay | trace_csv | ok |
| REQ-PBT-005 | - | PBT-005 | - | tests/pbt/test_kalman.py::TestKalmanFilter::test_estimation_error_bounded_nominal | failure_bundle, trace_csv | ok |
| REQ-SM-001 | - | PBT-004 | FML-002 | tests/assurance/test_formal_mode_logic.py::TestFormalModeLogic.test_formal_checker_passes_default_model | formal_report, failure_bundle | ok |
| REQ-SM-002 | - | - | FML-001 | tests/assurance/test_formal_mode_logic.py::TestFormalModeLogic.test_formal_checker_passes_default_model | formal_report | ok |

## Issues

- none

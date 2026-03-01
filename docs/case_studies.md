# Required Case Studies

## 1. Invalid Config Caught Preflight

Command:

```bash
python3 -m src.cli mcv validate configs/invalid_autonomous_abort.yaml
```

Expected: diagnostics include autonomous abort dependency violations (`MCV-016`, `MCV-017`) and validation exits non-zero.

## 2. Valid Config Fails Under Edge Conditions

Commands:

```bash
python3 -m src.cli mcv compile configs/valid_tight_aoa.yaml -o compiled_edge.json
python3 -m src.cli pbt run compiled_edge.json --runs 50 --profile degraded
```

Expected: config compiles successfully, but degraded randomized scenarios can produce safety/liveness violations and failure bundles.

## 3. Shrunk Counterexample Replay

Commands:

```bash
python3 -m src.cli pbt shrink failures/<bundle_dir>
python3 -m src.cli pbt replay failures/<bundle_dir>
```

Expected: shrinking reduces scenario complexity while preserving at least one property violation; replay produces deterministic failure outcome.

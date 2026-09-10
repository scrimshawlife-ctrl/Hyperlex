# scripts/shadow

SHADOW / advisory only. Not on Hyperlex API_V1. No Abraxas import.

`recoverable_structure` is Spec 004 (U1 DISCOVER-shaped probe).

```
PYTHONPATH=scripts/shadow python3 -m recoverable_structure.cli --fixture tpr --human
pytest -q tests/shadow/test_recoverable_structure_probe.py
```

`hyperlexical` is Spec 007 (U1 infer, U2 export, U3 eval/train-gate).

```
PYTHONPATH=scripts/shadow python3 -m hyperlexical.infer --text rizz --offline
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline
pytest -q tests/shadow/test_hyperlexical_shadow.py tests/shadow/test_hyperlexical_export.py tests/shadow/test_hyperlexical_eval.py
```

`eval_unbind` exit 3 means E2 not passed (expected on stub).
`train` exit 2 means the Spark gate is closed.

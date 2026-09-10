# scripts/shadow

SHADOW / advisory only. Not on Hyperlex API_V1. No Abraxas import.

`recoverable_structure` is Spec 004 (U1 DISCOVER-shaped probe).

```
PYTHONPATH=scripts/shadow python3 -m recoverable_structure.cli --fixture tpr --human
pytest -q tests/shadow/test_recoverable_structure_probe.py
```

`hyperlexical` is Spec 007 (U1 inference stub). No torch. No Hub download.

```
PYTHONPATH=scripts/shadow python3 -m hyperlexical.infer --text rizz --offline
pytest -q tests/shadow/test_hyperlexical_shadow.py
```

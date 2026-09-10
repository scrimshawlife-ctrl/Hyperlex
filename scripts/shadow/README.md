# scripts/shadow

SHADOW / advisory only. Not on Hyperlex API_V1. No Abraxas import.

`hyperlexical` is Spec 007.

```
PYTHONPATH=scripts/shadow python3 -m hyperlexical.infer --text rizz --offline
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind
PYTHONPATH=scripts/shadow python3 -m hyperlexical.preflight
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline
```

Spark smoke (Aaron): `specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md`

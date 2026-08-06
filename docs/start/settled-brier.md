# Why “settled Brier only”

## The problem
Many systems print a confidence or “accuracy” number on every run. That number is
easy to invent and hard to falsify. Readers treat it as skill when it is only a
decorative float.

## The rule
Hyperlex separates **claims** from **scores**:

1. **Open analysis** may emit forecasts (probabilities) and always sets
   `provenance.brier = null`.
2. An **operator** settles each forecast with an outcome (`TRUE` / `FALSE` / `VOID`).
3. Only then does **`score-series`** compute Brier (and related decompositions)
   from settled pairs.

Missing outcomes yield `NOT_COMPUTABLE` — never a fabricated score.

## Why this is a strength
- Auditable: scores attach to receipts + settlements.
- Honest: Phase 5 research cannot launder itself into calibration.
- Comparable: series Brier means the same thing over time.

## Operator path

```bash
python3 scripts/hyperlex.py pipeline "rizz" --route offline
python3 scripts/hyperlex.py pending
python3 scripts/hyperlex.py settle --forecast-id <id> --decision TRUE
python3 scripts/hyperlex.py score-series --mean-shift --verify-chain
```

## See also
- [Glossary](glossary.md#settled-brier-only)
- [Brier design](../brier-calibration.md)
- [Operator loop](../operator-loop.md)

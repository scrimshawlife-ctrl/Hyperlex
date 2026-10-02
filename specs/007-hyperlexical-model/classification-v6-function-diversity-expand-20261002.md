# EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION

```text
OUTCOME = V6_FUNCTION_DIVERSITY_NO_ADVANCE
NEXT_ACTION = REDESIGN_V6_FUNCTION_PREDICTION
diversity_pass = True
none_preserved = True

REP_V3 candidate (new heads, frozen gate):
  system = 0.2251
  DOMAIN = 0.1257
  FUNCTION = 0.1523
  MEDIATION = 0.3975
  positive-only = 0.2326
  zero-FP = 0.0262
  zero-exact = 0.9738

baseline old heads on REP_V3:
  FUNCTION = 0.2964
  positive-only = 0.3581
  zero-FP = 0.0877

Δ FUNCTION = -0.1441
Δ positive-only = -0.1255
```

## Research answer

Broader natural function supervision **did repair positive/function
representativeness** (diversity gates pass) and **preserved the frozen NONE
gate**, but **did not improve** FUNCTION / positive-only vs the old heads on
the same REP_V3. That earns `REDESIGN_V6_FUNCTION_PREDICTION`.

## Data changes (V2 → V3)

| surface | n | notes |
|---|---:|---|
| TRAIN_V3 | 3035 | +96 new function, +120 new domain/mediation positives |
| DEV_V3 | 540 | +35 new function |
| REP_V3 | 1511 | +55 new function, +40 other positives; zero-label 0.568 |

Acquire (SEED 20261004, QUAL-003 blocked): 734 NATURAL OBSERVED rows
(214 wiki-culture, 520 longer/multi-sense wikt). Dual-annotate + settled
family→function map. New train function mean max-sim to old train function
centroid neighbors ≈ 0.30 (farther neighborhoods).

## Diversity / support audit (pass)

- REP function n=241; non-wikt share **0.373**; medium+long **0.793**
- domain×function pairs **27**; per-function REP/TRAIN floors met
- disjointness OK; QUAL-003 blocked; zero-label in [0.55, 0.75]

## FUNCTION by label / source / length (candidate REP_V3)

| label | f1 | support |
|---|---:|---:|
| conflictive_force | 0.316 | 62 |
| relational_intimacy | 0.148 | 49 |
| memetic_form | 0.078 | 46 |
| evaluative_stance | 0.067 | 51 |

- by source: encyclopedic_positive ≈ 0.183; wiktionary ≈ 0.185
- by length: short 0.370; medium 0.019; long 0.131

## NONE preservation

Frozen ANY_LABEL th≈0.225 / gate sha `b7d93816…`. REP_V3 zero-FP **0.026**
(exact **0.974**) — operating gates pass; no regression vs witness.

## Frozen / rejected

encoder · ANY_LABEL · ontology · thresholds · QUAL-003 · architecture bakeoff
· QUAL-003 optimization — untouched. MODEL_WIDE_BEST unchanged.

Encoder / ANY_LABEL gate / ontology / thresholds frozen.
QUAL-003 blocked from train/acquisition targeting.
MODEL_WIDE_BEST unchanged. HUB_PUBLISH_AUTHORIZED = false.

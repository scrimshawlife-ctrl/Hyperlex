# Classification v5 — Stage-A uncertain-policy investigation

Parent: `HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS` (`SETTLED_FAIL`)  
SELECTED: `dba6d491…` · V1R8 `c0fdd82d…` · BEST unchanged `9fba0f66…`  
Gold mapping freeze: `HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1` (admission PASS, 0 mismatches)

```text
TRAIN = false
INVESTIGATION_STATE = COMPLETE
PRIMARY_DIAGNOSIS = MIXED_UNCERTAIN_FAILURE
UNCERTAIN_HEAD_SIGNAL = UNCERTAIN_HEAD_SIGNAL_PRESENT
NEXT_ACTION = AUDIT_V5_UNCERTAIN_LABEL_SURFACE
```

## 1. Probability geometry (validation)

| Gold | n | argmax PRESENT/NONE/UNC | mean P(PRESENT) | mean P(NONE) | mean P(UNC) | mean entropy | mean top1−top2 |
|---|---:|---|---:|---:|---:|---:|---:|
| EVIDENCE_PRESENT | 637 | 335/263/39 | 0.516 | 0.424 | 0.060 | 0.314 | 0.730 |
| NO_EVIDENCE | 1252 | 15/1228/9 | 0.023 | 0.967 | 0.010 | 0.065 | 0.954 |
| UNCERTAIN | 61 | 3/22/36 | 0.100 | 0.350 | 0.549 | 0.340 | 0.712 |

Full p10/p25/p75/p90 in private `PROBABILITY_GEOMETRY.json`.

## 2. PRESENT FN decomposition (scalar 0.50/0.55)

| Partition | n | OBSERVED | INFERRED |
|---|---:|---:|---:|
| PRESENT_CORRECT | 320 | 233 | 87 |
| PRESENT_TO_NONE | 303 | 298 | 5 |
| PRESENT_TO_UNCERTAIN | 14 | 14 | 0 |

FN taxonomy (misses only): `{'CALIBRATION_SHIFT': 59, 'GENUINELY_UNCERTAIN': 39, 'LOW_MARGIN_PRESENT': 25, 'NONE_DOMINATED': 194}`  
**Primary:** `NONE_DOMINATED` — missed PRESENT rows are mostly confident-NONE, not band UNCERTAIN.

## 3. UNCERTAIN head signal

```text
UNCERTAIN_HEAD_SIGNAL = UNCERTAIN_HEAD_SIGNAL_PRESENT
gold UNCERTAIN top1 = {'EVIDENCE_PRESENT': 3, 'NO_EVIDENCE': 22, 'UNCERTAIN': 36}
mean P(UNCERTAIN)|gold UNC = 0.549
mean P(UNCERTAIN)|gold PRESENT = 0.060
mean P(UNCERTAIN)|gold NONE = 0.010
```

The UNCERTAIN logit carries independent signal. Scalar `P(PRESENT)`-only policy
sets UNCERTAIN recall to **0** (absorbs too little / too late).

## 4–7. Policy replay (diagnostic; not production auth)

| Policy | false_entry | PRESENT R | NONE R | UNC R | macro-F1 | gates |
|---|---:|---:|---:|---:|---:|:---:|
| A scalar 0.50/0.55 | 0.0088 | 0.5024 | 0.9888 | 0.0000 | 0.5092 | no |
| A scalar full grid | — | — | — | — | — | n_passing=0 |
| B native argmax | 0.0120 | 0.5259 | 0.9808 | 0.5902 | 0.6872 | no |
| C margin 0.05–0.20 | — | — | — | — | — | n_passing_floors=0 |
| D dual-confidence grid | — | — | — | — | — | n_passing=0 |

**Gate-clearing diagnostic policies:** none.

Argmax restores UNCERTAIN recall (`0→0.59`) but does **not** lift PRESENT recall
to ≥0.70 (aggregate `0.526`; OBSERVED PRESENT `0.455`).

## 8. OBSERVED / INFERRED / ATOM / PROSE

OBSERVED PRESENT recall by policy: `{'A_scalar': 0.42752293577981654, 'B_argmax': 0.45504587155963305, 'C_margin_0_10': 0.42752293577981654, 'D_dual_best': None, 'n_obs_present': 545}`  
Policy choice does not fix the OBSERVED PRESENT-recall failure; it mainly
reallocates UNCERTAIN decisions.

## Decision

```text
PRIMARY_DIAGNOSIS = MIXED_UNCERTAIN_FAILURE
```

- Scalar policy under-uses a real UNCERTAIN head signal (too little / too late).
- No frozen diagnostic policy clears the three Stage-A gates.
- PRESENT misses remain predominantly `NONE_DOMINATED` (194/317), especially
  OBSERVED (`298/303` of PRESENT→NONE).

```text
NEXT_ACTION = AUDIT_V5_UNCERTAIN_LABEL_SURFACE
```

No train. No threshold production authorization. No reserve. BEST unchanged.
Gold mapping remains dataset-semantic under V1.

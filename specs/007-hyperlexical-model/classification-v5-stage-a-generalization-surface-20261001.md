# Classification v5 — Stage-A generalization surface v1

```text
ACTION = BUILD_V5_STAGE_A_GENERALIZATION_SURFACE_V1
surface = HYPERLEX_V5_STAGE_A_GENERALIZATION_SURFACE_V1
surface_version = classification-v5-stage-a-generalization-surface-v1-20261001
dataset_sha256 = 7567edcdf74c1033a07e3ae1d42b0e54ed0804b78fd7ba340c35752ac13df09f
state = PREREGISTERED
ready = false
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
spent_reserve = HYPERLEX_V5_PROMOTION_RESERVE_001 SPENT/IMMUTABLE (overlap=0)
V1R9 = 8d4be830… UNMUTATED
TRAIN = false
receipt = 424865ba…
next_action = REMEDIATE_V5_STAGE_A_GENERALIZATION_SURFACE_GATES
```

Matched-boundary Stage-A train/validation surface targeting surface-conditioned
generalization gaps from `STAGE_A_GENERALIZATION_FAILURE`. No training, no
threshold retune, no Stage-B mutation, no spent-reserve reuse, no BEST moves.

## Counts

| Split | n |
|---|---:|
| total | 2624 |
| train | 1907 |
| validation | 717 |

| Label | n |
|---|---:|
| EVIDENCE_PRESENT | 1223 |
| NO_EVIDENCE | 1202 |
| UNCERTAIN | 199 |

| Provenance | n |
|---|---:|
| OBSERVED | 1103 |
| INFERRED | 1521 |

## Primary cells (train / validation)

| Cell | train | validation | total |
|---|---:|---:|---:|
| SHORT_ATOM / NO_EVIDENCE | 114 | 116 | 230 |
| SHORT_ATOM / EVIDENCE_PRESENT | 113 | 116 | 229 |
| PROSE / NO_EVIDENCE | 192 | 69 | 261 |
| PROSE / EVIDENCE_PRESENT | 249 | 57 | 306 |
| DEFINITION_STYLE / NO_EVIDENCE | 243 | 89 | 332 |
| DEFINITION_STYLE / EVIDENCE_PRESENT | 226 | 82 | 308 |
| ORDINARY_PROSE / NO_EVIDENCE | 300 | 79 | 379 |
| ORDINARY_PROSE / EVIDENCE_PRESENT | 299 | 81 | 380 |

Critical validation floors (≥80) for SHORT_ATOM and DEFINITION_STYLE cells: **PASS**.
SHORT_ATOM train floors (≥150): **FAIL** (gaps 36 / 37).

## Matched contrast pairs

| Surface | pairs |
|---|---:|
| SHORT_ATOM | 229 |
| DEFINITION_STYLE | 279 |
| ORDINARY_PROSE | 160 |
| PROSE | 108 |
| **total** | **776** |

Pair membership is semantic (shared surface/domain/cues; missing core on NONE).
No model score admits pairs.

## Readiness gates

| Gate | Result |
|---|---|
| cell support floors | FAIL (SHORT_ATOM train) |
| source/provenance floors | FAIL (wiktionary_aggregate ~0.274 / ~0.279) |
| domain coverage | FAIL (astronomy, betting-sharp, crypto-degen, internet-slang, mathematics, technology-ai NONE short; near-domain PRESENT short) |
| disjointness | PASS |
| spent-reserve overlap | PASS (0) |
| surface-balance | FAIL (median token ratio 1.385) |
| lexical overlap | FAIL (top100 Jaccard 0.235; shared HF tokens 84 PASS) |
| embedding hardness | PASS (median opp cosine 0.972; frac≥0.75 = 0.981) |
| shallow shortcuts | FAIL (length BA 0.621; TF-IDF BA 0.772; surface BA/F1 PASS) |
| schema / gold invalid | PASS (0 invalid) |
| pairing floors | PASS |
| provenance (val OBSERVED≥50%; critical≥40%) | PASS |

Weighted readiness score: **not allowed**. Aggregate state: **PREREGISTERED**.

## Isolation

Spent reserve rows inform failure taxonomy only. Surface identities / source
hashes / parent lineage / near-duplicate components are disjoint from all spent
reserves, V1R9 train/val, historical held-out, and measurement-only surfaces.

## Artifacts (private)

```text
/home/morpheus/hlx-private/classification-v5-stage-a-generalization-surface-v1-20261001/
  EVIDENCE_SURFACE.jsonl
  MANIFEST.json
  SPLIT_MANIFEST.json
  CONTRAST_PAIR_WITNESS.json
  SOURCE_DOMAIN_WITNESS.json
  PROVENANCE_WITNESS.json
  DISJOINTNESS_WITNESS.json
  SHORTCUT_DIAGNOSTICS.json
  EMBEDDING_HARDNESS.json
  CELL_DIAGNOSTICS.json
  READINESS.json
  ARTIFACT_HASHES.json
```

## Exact next action

```text
REMEDIATE_V5_STAGE_A_GENERALIZATION_SURFACE_GATES
```

Do **not** authorize retrain until READY. Remediation targets:

1. SHORT_ATOM train mass (≥150 each side) without lifting wiktionary_aggregate above 0.25
2. Matched-length PRESENT/NONE mix (median token ratio ∈ [0.85, 1.18])
3. Domain-balanced NONE for astronomy / betting-sharp / crypto-degen / internet-slang / mathematics / technology-ai; PRESENT for near-domain
4. Lexical overlap (top100 Jaccard ≥ 0.35) via matched vocabulary, not TF-IDF leakage
5. Length-only BA ≤ 0.57 and TF-IDF BA ≤ 0.75 (no exception)

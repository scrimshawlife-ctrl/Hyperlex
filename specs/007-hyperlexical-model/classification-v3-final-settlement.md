# Classification v3 — final settlement

```text
HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE = SETTLED_FAIL
disposition = RESERVE_FAIL
BEST = UNCHANGED
spent_v2_reserve_reuse = false
recalibrated = false
```

Settlement date: 2026-09-30. Fresh v3 reserve (n=109 AVAILABLE identities) scored once under frozen Stage A/B thresholds after validation authorized the seal. No threshold retune. No BEST move.

## Verdict

Validation looked viable (false-entry ≈ 0.0059, family emission ≈ 0.815). The fresh reserve did not generalize:

| Metric | Validation | Reserve |
|---|---|---|
| false_evidence_entry_rate_on_none | 0.0059 | **0.25** |
| family_emission_precision | 0.815 | **0.0** |

Reserve composition was severely skewed (internet-slang 97 / none 8 / memetic 4), so the failure is both generalization and reserve-support poverty. Do not retune against this reserve.

## Frozen pins

| Artifact | sha256 / value |
|---|---|
| BEST | `9fba0f66…bbd97f6` |
| Stage A checkpoint | `0b7dbdac…420ce7` |
| Stage A thresholds | `none=0.05`, `present=0.55` |
| Stage B thresholds | `score≥0.96`, `margin≥0.01` |
| Stage B index | `42ae85f3…c40285` |
| Evidence surface | `7339c044…0d2d3a` |
| Reserve rows | see `classification-v3-reserve-receipt-20260930.json` |
| Reserve eval receipt | `61daa473…914ec` |

## Next action

```text
STOP — preserve v3 reserve result; do not retune thresholds against the reserve; do not move BEST.
```

A later generation needs a balanced fresh reserve acquisition before another evidence-gate climb.
That climb is opened under `HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_ACQUIRE_V1`
(`classification-v4-balanced-reserve-acquire.md`). Remaining fresh AVAILABLE classify
identities after spent-v3 exclusion: 0 — Wiktionary acquire is required.

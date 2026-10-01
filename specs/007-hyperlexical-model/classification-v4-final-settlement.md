# Classification v4 — balanced reserve final settlement

```text
HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_EVAL_V1 = SETTLED_FAIL
disposition = RESERVE_FAIL
parent_acquire = ACQUIRE_READY (n=176; floors met)
BEST = UNCHANGED
spent_v2_reserve_reuse = false
spent_v3_reserve_reuse = false
recalibrated = false
train = false
```

Settlement date: 2026-09-30. The ACQUIRE_READY Wiktionary pool was sealed as the
fresh promotion reserve and scored once under frozen Stage A/B thresholds.
No threshold retune. No BEST move. All 176 identities marked `evaluation_spent`.

## Verdict

Balance floors were met (none=48, present=128, 16 families, max share 0.0625).
The frozen evidence gate still did not generalize:

| Metric | Stage B validation | v4 balanced reserve |
|---|---|---|
| false_evidence_entry_rate_on_none | 0.0059 | **0.4167** |
| family_emission_precision | 0.815 | **0.4545** |

Decision counts: ABSTAIN 121 / AMBIGUOUS 24 / FAMILY 11 / NONE 20.  
Primary failure remains Stage A false-present on HARD_NONE ordinary-domain
Wiktionary definitions (~20/48 none entered retrieval). Family emission
improved vs the skewed v3 scoop but stays below 0.80. Do not retune against
this reserve.

## Frozen pins

| Artifact | sha256 / value |
|---|---|
| BEST | `9fba0f66…bbd97f6` |
| Stage A checkpoint | `0b7dbdac…420ce7` |
| Stage A thresholds | `none=0.05`, `present=0.55` |
| Stage B thresholds | `score≥0.96`, `margin≥0.01` |
| Stage B index | `42ae85f3…c40285` |
| Acquire / reserve rows | `dd224047…794eb82` |
| Reserve eval receipt | `ffa5c603…691ccea` |

## Next action

```text
STOP — preserve v4 balanced reserve result; do not retune thresholds against the reserve; do not move BEST.
```

A later climb needs Stage A remediation against ordinary-domain / HARD_NONE
surfaces before another promotion reserve score. Spent v2/v3/v4 reserves
remain permanently excluded.

# rc2 pre-registration — post-rc1 clean retrain (2026-09-26)

**Operator:** Danny `continue training according to our updated contents` (this session).  
**Authority shape:** same class as rc1's `okay continue as recommended` — clean release retrain + one test score. Not a morph soft_ceiling climb. Not Hub. Not T13. Not `name_gate` move.

Committed **before** training. Holdout bytes must be frozen and hashed before launch.

## Why not re-run rc1

rc1 **REJECT** (`receipts/rc1-result-20260924/OPERATOR-CARD.md`). Holdout `holdout-manifest-rc1.json` is **`SCORED_SPENT`**. Soft_ceiling morph78 climb is spent. Selection-surface audit = **NO_RULE_MATCH / HOLD**.

Updated `main` since rc1 train SHA `ed27545` adds fail-closed holdout exclusion (#120) and force-train disjoint (#122 family). rc2 must use those.

## Candidate

`seed-rc2` = rc1 recipe + current-main guards (`scripts/spark/soft_ceiling/rc2-train-env.json`):

1. **Cold start** (no `HYPERLEX_INIT_FROM`).
2. `HYPERLEX_FILLER_FILTER=strict` (D8).
3. `HYPERLEX_RELEASE_SET=1` (D5b).
4. `HLX_HOLDOUT_MANIFESTS` → **new** `holdout-manifest-rc2.json` (fail-closed; do not set `HLX_ALLOW_NO_HOLDOUT`).
5. `HLX_FORCE_TRAIN_DISJOINT=1` — drop force/hard overlap from the scored val surface used during train accounting (anti-contamination from publish audit B1).
6. Classify harness flags stay **default-off** (`HLX_VOCAB_TRAIN_ONLY`, `HLX_SELECT_METRIC`, `HLX_CLASSIFY_ADMISSION` unset).
7. Same knobs as rc1 otherwise: 40 ep, lr 2e-5, batch 8, LAST=8, OBSERVED upsample 10, legacy task routing, morph78 force/hard paths.

PRIOR for gates: **`seed-morph78`** (BEST). Also score morph65 for the table.

## Frozen evaluation (draw on Spark before train)

Path: `receipts/rc2-prereg-20260926/holdout-manifest-rc2.json`  
Status must be `FROZEN_NOT_SCORED` at commit/launch.  
Do **not** reuse rc1 row ids. Census first (`heldout_census.py` / `flag_rows.py`), then `holdout_manifest.py`.

Exclude every row in morph78/morph50 force/hard files (rc2 trains on morph78 force/hard) and train text, on the release surface.

## Decision rule (stated in advance)

rc2 is the **release candidate** if all hold:

1. Trained trunk-forward E2 PASS.
2. Corrected soft_ceiling on clean val not below morph78 (tie OK).
3. Test non-inferiority vs morph78: unbind clean exact ≥ morph78 − 0.01; classify all ≥ morph78 − 0.02; classify OBSERVED ≥ morph78 − 0.05.
4. Test classify > `classify_majority_train`.
5. Shipped `filler_vocab` passes `assert_publishable_vocab`.

If rc2 fails: BEST stays morph78; record REJECT; no Hub; `name_gate` stays on morph78.

## Hard nos

- Re-score spent rc1 holdout for selection
- Soft_ceiling morph79 without named-phrase authorize card
- Hub / T13 / extend `name_gate`
- `HLX_ALLOW_NO_HOLDOUT=1`
- Upsample 11+ / `SECOND_SLOT=4`
- Train from org mirror

## Blocker this session

Cloud Agent reached `ssh.zer0state.com` via cloudflared Access but has **no morpheus SSH private key** (`Permission denied (publickey)`). Qwen gateway `qwen.zer0state.com` returns **502**. Train launch is **parked** until Spark SSH works from an authorized host. Runbook: `SPARK-RC2-RUN.md`.

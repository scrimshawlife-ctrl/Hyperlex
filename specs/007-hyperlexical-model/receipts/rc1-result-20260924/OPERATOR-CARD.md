# rc1 result — REJECT (2026-09-24, PT)

**Decision: REJECT. rc1 is not the release candidate. BEST is unchanged (`seed-morph78`). name_gate was not touched. No Hub upload. Nothing committed.**

Pre-reg: `../20260924-rc1-preregistration.md` · Manifest: `../rc1-prereg-20260924/holdout-manifest-rc1.json` (verified by `score_holdout.py`: all four slice row-ID hashes match, code tree `736bb3fc…` = manifest).
Machine-readable decision: `pin-reject.json`.

## What "complete" meant (pre-reg)
Train rc1 once (cold start, strict filler filter, release set; done 15:20–19:15 PT, exit 0), then score rc1 + morph78 + morph65 **once, together** on the frozen test holdout with val-fitted calibration, and apply the 5-part rule. The pre-reg calls for no more training (no extra seeds, no final fit).

## Decision rule (all must hold)
| # | Criterion | rc1 | morph78 | Threshold | Result |
|---|---|--:|--:|--:|---|
| 1 | Trunk-forward E2 | unbind_exact 1.0, e2_pass | — | PASS | **PASS** |
| 2 | Corrected soft_ceiling, clean val (release surface, n=51, overlap 0) not below morph78 | 1.000 | 1.000 | tie OK | **PASS** (tie; gate verdict `REJECT_VS_BROAD_BASELINE`, recorded) |
| 3a | Test unbind clean exact (n=306) | 0.6797 (208/306) | 0.7255 (222/306) | ≥ 0.7155 | **FAIL** (0.036 short) |
| 3b | Test classify accuracy, all (n=444) | 0.7905 (351/444) | 0.8176 (363/444) | ≥ 0.7976 | **FAIL** (0.007 short) |
| 3c | Test classify accuracy, OBSERVED (n=72) | 0.5694 (41/72) | 0.6389 (46/72) | ≥ 0.5889 | **FAIL** (0.019 short) |
| 4 | Test classify > `classify_majority_train` (0.6486, `none`) | 0.7905 | — | > 0.6486 | **PASS** |
| 5 | Shipped `filler_vocab` (1,480) passes `assert_publishable_vocab` | pass | — | — | **PASS** |

## Full test table (reported regardless)
| Model | unbind all (312) | unbind clean (306) | OOV-filler (10) | clean tokF1 | cls acc | cls macroF1 | cls OBS (72) | cls INF (372) | ECE | abstain | T / thr |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| rc1 | 0.6731 | 0.6797 | 0.10 | 0.837 | 0.7905 | 0.567 | 0.5694 | 0.8333 | 0.063 | 0.387 | 2.65 / 0.740 |
| morph78 | 0.7212 | 0.7255 | 0.10 | 0.865 | 0.8176 | 0.621 | 0.6389 | 0.8522 | 0.056 | 0.243 | 5.45 / 0.618 |
| morph65 | 0.6955 | 0.6993 | 0.00 | 0.852 | 0.8198 | 0.608 | 0.6389 | 0.8548 | 0.054 | 0.189 | 5.40 / 0.584 |

Baseline `unbind_copy_token` = 1.0 on all/clean/OOV (it only checks that the gold fillers appear among the atom tokens, not the slot assignment). All three models sit 0.27–0.32 below it and far below their ~1.0 val unbind. That is a large val-to-test gap for every model, not only rc1.

## Calibration (clean val, fitted before test)
Surface: release-set classify val, same exclusions as the manifest (4 force/hard files), n=356 (OBS 63 / INF 293), identical for all three models. rc1 acc 0.764 (T 2.65, ECE 0.163 to 0.038); morph78 0.803 (T 5.45); morph65 0.801 (T 5.40).
Interpretation note: the pre-reg says "its clean val". We used one shared release-set clean-val surface for all three, the same data and exclusions as the frozen holdout. The older publish-readiness morph78 calibration (non-release val, n=402, T 5.1) was not reused.

## Runs
All on Morpheus, image `lmsysorg/sglang:dev-qwen38-27b-dflash2`, training mount pattern, every python step via `scripts/spark/guard.py 0.3`.
- `hlx-eval-rc1-1790308987`: `run-phaseA-val.sh` (val only: E2, eval_broad x2, calibrate x3). 21:03:07–21:05:01 PT, exit 0. RAM before: 118 GB available.
- `finish.py` on host (no torch, **no `--apply-best`**) wrote `verdict-soft-ceiling-clean-rc1-vs-morph78.json` at 21:05:25 PT. The `--fair` input reused `../morph78-val-settle-20260924/fair-eval-morph65-morph78.json`, exactly as the 2d verdict did. force_fair=1.0 only routes the gate to ceiling mode; the decision is the clean broad comparison.
- `hlx-eval-rc1-test-1790309133`: `run-phaseB-test.sh` (the single test score). 21:05:34–21:06:28 PT, exit 0. Weight sha256: rc1 `5949d880…` (top-level = best/); morph78 `fc53676b…` and morph65 `96838b96…` both match the manifest.
- Container env: HOME, PYTHONPATH=scripts/shadow:scripts/spark/soft_ceiling, HF_HUB_OFFLINE=1, HYPERLEX_OFFLINE=1, HYPERLEX_INCLUDE_LIVE=1, HYPERLEX_RELEASE_SET=1, HYPERLEX_FILLER_FILTER=strict, HYPERLEX_TASK_ROUTING=legacy_split, HYPERLEX_CUDA_MEM_FRACTION=0.3, HYPERLEX_TRUNK_DIR. calibrate/score also load `--env scripts/spark/soft_ceiling/rc1-train-env.json`.
- Exact commands are in the two `run-phase*.sh` scripts (copied here) and in `docker logs` of the two containers.
- Filler vocab check: `hyperlexical.filler_filter.assert_publishable_vocab` on `rc1/config.json` and `rc1/best/config.json` (identical, 1,480 entries), host python, about 21:02 PT.

## State after
- `~/.hyperlex/models/BEST` points to `…seed-morph78`, unchanged (it was morph78 before). No rollback needed.
- The test split is **burned for selection**. The manifest file was left untouched and still says `FROZEN_NOT_SCORED`; marking it scored is a follow-up for Danny. `score_holdout.py` only refuses an existing `--out`, so it would re-score to a new path.
- No gold/SoT mutation, no git commit, no containers stopped or removed. The receipts folder is untracked in git.

## Conflict with the ne0l0gist morph-cycle skill
The pre-reg governs rc1. The skill pin rule (val unbind_exact must **beat** BEST, plus E2 = 1.0) would also reject: rc1 val 0.993 (n=140) vs morph78 1.0 (n=164), and those val surfaces differ anyway. The pre-reg uses non-inferiority margins on test instead of strict improvement on val.
The skill "Freeze" knobs (LAST_TRAINABLE=4, 6 epochs, OBSERVED_UPSAMPLE=2) are stale compared with the morph78/rc1 recipe (8 / 40 / 10).
The skill receipt location (`Desktop/hyperlex-spark-sync/receipts-morphN/`, `BEST-CHECKPOINT.md`) was not used. There was nothing to update, since BEST did not move.

## Next (needs Danny)
rc1, the clean-data retrain, ties morph78 on clean val but misses all three test non-inferiority margins. Options: keep morph78 as BEST (the current state), or accept the clean-data trade-off by operator sentence. Any further climb needs a new holdout drawn and hashed before training (manifest rule 4).

## Addendum 2026-09-24 ~21:20 PT: manifest marked spent (Danny yes)
`holdout-manifest-rc1.json` status changed from `FROZEN_NOT_SCORED` to `SCORED_SPENT`. Added `scored_at`, `scored_by_container`, `scored_decision_receipt`, `scored_scores_receipt`, and `scored_note`. No slice, code or weight hash changed. The original is backed up byte-identical (sha256 `5328c1aa…`, same as git HEAD ff5ec92) at `holdout-manifest-rc1.json.pre-scored-20260924`. `score_holdout.py` now refuses this manifest, as intended. Slice hashes still re-derive and match (checked without scoring).

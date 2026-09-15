# Receipt — morph36 40ep IN FLIGHT (best-ckpt save)

**Date:** 2026-09-15  
**Authority:** Spec 007. Operator continue after morph35 KEEP_CANDIDATE.  
**BEST:** morph19 — **untouched** (`promote_best=false`). `name_gate=false`. No Hub.  
**Danny gold:** still **PENDING** — no invented OBSERVED.

## Decision

| check | result |
|-------|--------|
| Danny OBSERVED gold landed? | **No** |
| morph35 KEEP_CANDIDATE on Hyperlex main? | **Yes** (PR #68 squash-merged) |
| Train chosen | **Civilian morph36** — morph19 envelope + **save best by val unbind_exact** |

## Init choice (documented)

**Chose morph19 envelope + trunk init** (same as morph35), **not** warm-load morph35 final.

Reason: morph35 final (0.4904) is **post-peak**; peak ep16 (0.5372) was never checkpointed. Warm-starting morph35 final would begin from degraded weights. Re-running the schedule with `HYPERLEX_SAVE_BEST_UNBIND=1` is the fix for peak-not-saved.

## Recipe

| knob | value |
|------|------:|
| out | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph36` (**new**) |
| init | ModernBERT-base trunk (no BEST / no morph35 warm-load) |
| epochs / batch / lr / last_n | **40** / 8 / 2e-5 / 4 |
| primary | `slot_ce` |
| HEAD_SLOT | 2 |
| OBSERVED / HARD upsample | 2 / 4 |
| hard atoms | existing `~/hlx/hard_atoms_train.jsonl` only |
| **SAVE_BEST_UNBIND** | **1** (primary `model.safetensors` = best val exact; final → `model.final.safetensors`) |
| invented OBSERVED gold? | **No** |

## Gate plan (no promote)

Compare primary (best-saved) vs morph19 (0.4545) and morph35 final (0.4904).  
**KEEP_CANDIDATE** if beats morph35 + E2 PASS; **do not** promote BEST.  
Only note promote if operator would need to say yes.

## Artifacts

- Container: `hlx-train-morph36-1789502369`
- Spark private: `~/hlx-private/p1-spark-morph36-40ep-bestckpt-20260915/`
- Intent: `morph36-intent.json`

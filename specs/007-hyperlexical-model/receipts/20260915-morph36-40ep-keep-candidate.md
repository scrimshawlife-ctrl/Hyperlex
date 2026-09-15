# Receipt — morph36 40ep KEEP_CANDIDATE (best-ckpt; no BEST promote)

**Date:** 2026-09-15  
**Authority:** Spec 007. Continue after morph35 KEEP_CANDIDATE.  
**BEST:** morph19 — **untouched** (`promote_best=false`, mtime unchanged). `name_gate=false`. No Hub.  
**Danny gold:** still **PENDING** — no invented OBSERVED.

## Decision tree

| check | result |
|-------|--------|
| Danny OBSERVED gold landed? | **No** |
| morph35 on Hyperlex main? | **Yes** (PR #68) |
| Train chosen | **Civilian morph36** — morph19 envelope + **save best by val unbind_exact** |

## Init choice (documented)

**Chose morph19 envelope + trunk init** (same as morph35), **not** warm-load morph35 final.

Reason: morph35 final (0.4904) is post-peak vs unsaved ep16 peak (0.5372). Re-running the schedule with `HYPERLEX_SAVE_BEST_UNBIND=1` captures the peak.

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
| **SAVE_BEST_UNBIND** | **1** → primary `model.safetensors` = best; final → `model.final.safetensors` |
| invented OBSERVED gold? | **No** |

## Gate (no promote)

| metric | morph19 BEST | morph35 final | morph36 **best** (ep23) | morph36 final |
|--------|-------------:|--------------:|------------------------:|--------------:|
| unbind_exact | 0.4545 | 0.4904 | **0.5455** | 0.5124 |
| token_f1 | 0.6976 | 0.7468 | **0.7714** | — |
| slot_f1 | 0.6966 | 0.7457 | **0.7714** | — |
| partial_slot_miss | 146 | 143 | **134** | — |
| E2 trunk-forward | PASS | PASS | **PASS** (`unbind_exact=1.0`) | — |

**Verdict: KEEP_CANDIDATE** — primary (best-saved) exact **>** morph35 final and **>** morph19; E2 PASS.  
**Promotion: deferred** — `promote_best=false`. Near ladder **0.55** (0.5455); operator would need to say yes to promote BEST.

Peak-not-saved fix: best ep23 weights are primary `model.safetensors` (final alone would have been 0.5124).

## Residual themes (best / primary)

`partial_slot_miss=134`, `type_slot_token_miss=69`, `positional_head_filler_miss=24`, `full_miss=15`, `morph_bleed=14`.

## Artifacts

- Spark private: `~/hlx-private/p1-spark-morph36-40ep-bestckpt-20260915/`
- Workspace: `specs/007-hyperlexical-model/receipts/morph36-40ep-bestckpt-20260915/`
- Container: `hlx-train-morph36-1789502369` (exit 0)
- Code: `HYPERLEX_SAVE_BEST_UNBIND` in `scripts/shadow/hyperlexical/loop.py`
- qwen restarted after gate

## Next

- Danny gold still required for OBSERVED `partial_slot_miss` / accept30+
- Optional: operator **yes** to promote BEST → morph36 (near 0.55) — not auto
- Do **not** invent OBSERVED gold; do **not** overwrite BEST without promote yes

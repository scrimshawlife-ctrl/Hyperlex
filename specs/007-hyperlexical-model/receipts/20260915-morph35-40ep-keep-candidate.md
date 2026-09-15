# Receipt — morph35 40ep KEEP_CANDIDATE (no BEST promote)

**Date:** 2026-09-15  
**Authority:** Spec 007. Operator override: continue training while Danny gold escalate pending.  
**BEST:** morph19 — **untouched** (`promote_best=false`, mtime unchanged). `name_gate=false`. No Hub.  
**Climb KEEP:** famcls52 — unchanged (holdout saturated; famcls53 skipped).

## Decision tree

| check | result |
|-------|--------|
| Danny OBSERVED gold landed? | **No** — 198 candidates still blank / PENDING |
| Climb holdout saturated? | **Yes** — famcls52 all 1.0 on accept29 |
| Train chosen | **Civilian morph35** (not famcls53) |

## Recipe

morph19 envelope; **schedule lever only** (`epochs=40`; morph19/morph34 used 6).

| knob | value |
|------|------:|
| out | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph35` (**new**) |
| init | ModernBERT-base trunk (morph19 lineage; no BEST warm-load) |
| epochs / batch / lr / last_n | **40** / 8 / 2e-5 / 4 |
| primary | `slot_ce` |
| HEAD_SLOT | 2 |
| OBSERVED / HARD upsample | 2 / 4 |
| hard atoms | existing `~/hlx/hard_atoms_train.jsonl` only |
| INFERRED weight / cap | 1.0 / 0 |
| curriculum POS/TYPE | 1 / 1 |
| morph_margin / loss | 0.5 / 1.0 |
| invented OBSERVED gold? | **No** |

`data_sha256` = see `train-receipt.json` in companion bundle.

## Gate (no promote)

Baseline morph19 civilian val `unbind_exact` = **0.454545…** (n=363).

| metric | morph19 BEST | morph35 final | morph35 peak (ep16) |
|--------|-------------:|--------------:|--------------------:|
| unbind_exact | 0.4545 | **0.4904** | **0.5372** |
| token_f1 | 0.6976 | 0.7468 | 0.7628 |
| slot_f1 | 0.6966 | 0.7457 | 0.7628 |
| partial_slot_miss | 146 | **143** | — |
| E2 trunk-forward | PASS | **PASS** (`unbind_exact=1.0`) | — |

**Verdict: KEEP_CANDIDATE** — final exact **>** morph19 and E2 PASS.  
**Promotion: deferred** — operator pin said gate without promoting; BEST symlink still morph19.

Note: trainer persists **final** epoch weights only. Peak ep16 exact **0.5372** is receipt-only (near ladder 0.55) and was not checkpoint-saved.

## Residual themes (final)

`partial_slot_miss=143`, `type_slot_token_miss=76`, `positional_head_filler_miss=32`, `full_miss=17`, `morph_bleed=12`.

## Artifacts

- Spark private: `~/hlx-private/p1-spark-morph35-40ep-20260915/`
- Workspace: `specs/007-hyperlexical-model/receipts/morph35-40ep-20260915/`
- Container: `hlx-train-morph35-1789496045` (exit 0)
- qwen restarted after gate

## Next

- Danny gold still required for OBSERVED `partial_slot_miss` policy / accept30+
- Optional: best-checkpoint save / resume-from-ep16 if operator authorizes (still no invented gold)
- Do **not** overwrite BEST without explicit promote approval

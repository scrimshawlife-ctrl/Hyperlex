# ESCALATE — Danny / OBSERVED partial_slot_miss

**Date:** 2026-09-15  
**Authority:** Spec 007. `name_gate=false`. No Hub. No invented OBSERVED gold.  
**BEST:** morph19 **untouched**. Climb KEEP **famcls52** ≠ BEST. **No auto-promote.**

## Marks evidence

| mark | status | evidence |
|------|--------|----------|
| Climb holdout family/structure/role/pointer all 1.0 | **HIT** | famcls52 SMOKE holdout_test all 1.0 on accept29 |
| Climb KEEP pin current famcls52 | **HIT** | `~/hlx-private/p1-structure-unbind-famcls52-20260914/` |
| Civilian unbind_exact receipt famcls52 vs morph19 | **HIT** | `climb_vs_best_civilian.json` |
| Ladder unbind_exact ≥ 0.55 | **MISS** | morph19 ≈0.4545; famcls52 transfer ≈0.0028 |
| Exhaust → Danny escalate | **HIT** | this receipt — **waiting on Danny** |

## Civilian scores (same val surface)

Surface: `export_dataset(include_live=True)` unbind `split=val`, **n=363**.

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss | n_residual |
|-------|-------------:|---------:|--------:|------------------:|-----------:|
| **morph19 BEST** | **0.4545** | 0.6976 | 0.6966 | **146** | 198 |
| famcls52 transfer (climb encoder + morph19 filler_head) | **0.0028** | 0.1015 | 0.0994 | 43 | 362 |

Scoring note: famcls52 native heads are family/role/pointer (structure climb). Civilian filler `unbind_exact` uses morph19 `filler_head` over the climb encoder as a transfer probe. Climb ≪ BEST on the ladder metric (Δ exact ≈ −0.452).

## Why escalate (not another famcls train)

1. Climb holdout already **1.0 / 1.0 / 1.0 / 1.0** — no climb residual to dump→accept→train.
2. Civilian ladder stuck: morph19 **0.4545** cleared **0.45**, not **0.55**.
3. Dominant morph19 residual theme: **`partial_slot_miss=146`** (also type_slot_token_miss=81, positional_head_filler_miss=36, full_miss=28, morph_bleed=11).
4. Structure-climb KEEP does **not** transfer to civilian filler unbind.
5. Morph envelope levers previously exhausted (morph22–34). Protocol: do **not** invent OBSERVED gold; do **not** auto-promote.

## Ask for Danny

Settle **OBSERVED** gold targeting `partial_slot_miss` (and related type_slot / positional head misses) on the civilian unbind val wall — or explicitly authorize a different ladder path. Until then: **waiting on Danny**. Keep `name_gate=false`. BEST stays morph19.

## Artifacts

- Spark: `~/hlx-private/climb_vs_best_civilian.json`
- Spark: `~/hlx-private/climb_vs_best_civilian_20260915/` (JSON + residuals)
- Workspace: `specs/007-hyperlexical-model/receipts/climb_vs_best_civilian.json`
- Climb pin: `~/hlx-private/p1-structure-unbind-famcls52-20260914/{KEPT.md,SMOKE_SUMMARY.json}`

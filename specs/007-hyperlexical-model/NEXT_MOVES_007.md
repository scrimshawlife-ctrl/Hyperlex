# Spec 007 — morph36 BEST; morph39 OBSERVED-gold REJECT_VS_BEST

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.
**BEST:** **morph36** — `unbind_exact≈0.5455` (old val n=363). Climb KEEP ≠ BEST. famcls52 holdout **1.0**.

## Status

morph36 promoted → BEST (operator yes).  
morph37 / morph38 warm → **REJECT_VS_BEST**.  
**Labeler AUTHORIZED 2026-09-16** (METHOD + 136 auth / 10 abstain on P1).  
morph39 → **REJECT_VS_BEST** (best 0.5621) vs fair morph36 **0.5740**; fair val shifted **363→338**. BEST stays morph36.

## Marks status (2026-09-16)

| mark | status |
|------|--------|
| morph36 BEST | **HIT** (held) |
| morph37 / morph38 warm | **HIT** → REJECT_VS_BEST |
| Danny/operator OBSERVED `partial_slot_miss` gold | **HIT** (authorized + labeled) |
| morph39 observed-gold force-train | **HIT** → **REJECT_VS_BEST** |
| Ladder `unbind_exact` ≥ **0.55** (old val n=363) | **MISS** (morph36 0.5455) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| **morph36 BEST** | 363 | **0.5455** | current BEST pin |
| morph36 fair (force-train val) | 338 | **0.5740** | baseline after removing 25 OBSERVED exacts |
| morph39 best ep2 | 338 | 0.5621 | REJECT vs fair |
| morph38 best | 363 | 0.5234 | REJECT |
| morph37 best | 363 | 0.5317 | REJECT |

## Pins

| pin | path | note |
|-----|------|------|
| **BEST** | morph36 | held after morph39 reject |
| morph39 | `...-seed-morph39` | REJECT_VS_BEST; E2 PASS |
| **Danny package** | `receipts/danny-gold-review-partial-slot-miss-20260915/` | labeled |
| **auth receipt** | `receipts/20260916-labeler-authorized-observed-gold.md` | |
| **morph39 gate** | `receipts/20260916-morph39-40ep-reject-vs-best.md` | |

## Next

- BEST stays morph36. Do not warm-clone morph40 without a new lever / operator ask.
- Force-train of the 25 OBSERVED P1 exacts removed them from val but did not improve generalization on remaining val vs morph36.
- Remaining P1 INFERRED labels are documentary only (no class promote). **No invent beyond labeled set.**
- Ladder ≥0.55 on **old** val n=363 still MISS.

## Policy

`name_gate=false`. Labeler authorized. Climb KEEP ≠ BEST. Full 40-epoch runs. One documented lever per climb. Fair-eval when val changes. No invent beyond labeled set.

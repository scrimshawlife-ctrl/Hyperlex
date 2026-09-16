# Spec 007 — morph41 IN FLIGHT (warm morph40; no new gold)

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST held:** **morph40** — `unbind_exact≈0.7368` (ep9) on fair val **n=228**. morph36 artifacts preserved. Climb KEEP famcls52 ≠ BEST.

## Status

morph40 BEST confirmed on spark. Civilian residual dump: **60** (PSM **28**).  
Residual review: **20** authorized structure / **8** abstain / **0** train promote → **NO_NEW_GOLD_THIS_CLIMB**.  
**morph41** warm morph40 + SAVE_BEST_UNBIND 40ep on existing gold 135/180 — **IN FLIGHT** (`hlx-train-morph41-1789537012`). Gate vs fair morph40 **0.7368**.

## Marks status (2026-09-16)

| mark | status |
|------|--------|
| morph36 BEST | **HIT** then **superseded** (artifacts preserved) |
| morph37 / morph38 warm | **HIT** → REJECT_VS_BEST |
| Danny/operator P1 gold | **HIT** (authorized + labeled) |
| morph39 observed-gold force-train | **HIT** → REJECT_VS_BEST |
| INFERRED→OBSERVED train promote | **HIT** (110 / 1 hold / 10 abstain) |
| morph40 inferred-promote | **HIT** → **PIN BEST** |
| morph40 residual review | **HIT** → no new gold |
| morph41 warm morph40 | **IN FLIGHT** |
| Ladder `unbind_exact` ≥ **0.55** (comparable new val n=228) | **HIT** (0.7368) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| morph36 fair morph40 | 228 | 0.7325 | after 135 force-train |
| **morph40 BEST ep9** | **228** | **0.7368** | **PIN / morph41 fair gate** |
| morph40 final ep39 | 228 | 0.6930 | SAVE_BEST kept ep9 |
| morph41 | 228 | TBD | warm morph40 IN FLIGHT |

## Pins

| pin | path | note |
|-----|------|------|
| **BEST** | morph40 | `...-seed-morph40` |
| morph36 | `...-seed-morph36` | preserved prior BEST |
| **residual review** | `receipts/morph40-residual-review-20260916/` | 20 auth / 0 promote |
| **morph41 inflight** | `receipts/20260916-morph41-40ep-inflight.md` | |

## Next

- Await morph41 40ep + E2; promote only if best > fair morph40 **0.7368**; else keep morph40 BEST.
- 20 authorized morph40 PSM held (not force-trained); 10 prior abstain + 1 documentary hold stay out.
- `name_gate` remains false. No Hub. No invent beyond labeled set.

## Policy

`name_gate=false`. Labeler authorized. Climb KEEP ≠ BEST. Full 40-epoch runs. One documented lever per climb. Fair-eval when val changes. No invent beyond labeled set.

# Spec 007 — morph43 REJECT_VS_BEST; BEST stays morph40

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST held:** **morph40** — prior fair n=228 `unbind_exact≈0.7368` (ep9). morph36 preserved. Climb KEEP famcls52 ≠ BEST.

## Status

morph40 BEST confirmed on spark.  
**morph41** warm morph40 @ mem **0.015** — **REJECT_VS_BEST** (best **0.7149**).  
**morph42** warm morph40 @ mem **0.3** — **REJECT_VS_BEST** (best **0.7149**; ~87 min; no wall speedup).  
**morph43** held residual gold @ mem **0.3** — **REJECT_VS_BEST** (best **0.9379** ep2 < fair morph40 **0.9492** on n=177; final 0.8870; ~86.3 min; E2 PASS).

## Marks status (2026-09-16)

| mark | status |
|------|--------|
| morph36 BEST | **HIT** then **superseded** (artifacts preserved) |
| morph37 / morph38 warm | **HIT** → REJECT_VS_BEST |
| Danny/operator P1 gold | **HIT** (authorized + labeled) |
| morph39 observed-gold force-train | **HIT** → REJECT_VS_BEST |
| INFERRED→OBSERVED train promote | **HIT** (110 / 1 hold / 10 abstain) |
| morph40 inferred-promote | **HIT** → **PIN BEST** |
| morph40 residual review | **HIT** → no new gold (held for morph43) |
| morph41 warm morph40 @ 0.015 | **HIT** → **REJECT_VS_BEST** |
| morph42 warm morph40 @ **0.3** | **HIT** → **REJECT_VS_BEST** (same peak 0.7149; ~87 min) |
| morph43 held-gold @ **0.3** | **HIT** → **REJECT_VS_BEST** (0.9379 < fair 0.9492 n=177) |
| Ladder `unbind_exact` ≥ **0.55** (comparable new val n=228) | **HIT** (0.7368) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| morph36 fair morph40 | 228 | 0.7325 | after 135 force-train |
| **morph40 BEST ep9** | **228** | **0.7368** | **PIN / held** (pre-morph43 val) |
| morph40 fair morph43 gate | **177** | **0.9492** | after +51 force-train; gate bar |
| morph41 best ep3 @ 0.015 | 228 | **0.7149** | REJECT vs fair 0.7368 |
| morph42 best ep3 @ **0.3** | 228 | **0.7149** | REJECT vs fair 0.7368 |
| morph43 best ep2 @ **0.3** | **177** | **0.9379** | REJECT vs fair 0.9492 |
| morph43 final ep39 | 177 | 0.8870 | below best |

## Pins

| pin | path | note |
|-----|------|------|
| **BEST** | morph40 | `...-seed-morph40` |
| morph36 | `...-seed-morph36` | preserved prior BEST |
| morph41 | `...-seed-morph41` | REJECT; weights kept |
| morph42 | `...-seed-morph42` | REJECT; weights kept |
| morph43 | `...-seed-morph43` | REJECT; weights kept |
| **morph43 gold** | `receipts/morph43-held-gold-promote-20260916/` | +51 force / +46 hard |
| **morph43 reject** | `receipts/20260916-morph43-40ep-reject-vs-best.md` | fair 0.9492 n=177 |
| **morph42 reject** | `receipts/20260916-morph42-40ep-reject-vs-best.md` | mem 0.3; ~87 min |

## Next

- **Do not** re-warm morph40 with the same gold. morph43 already integrated the held residuals and missed the raised fair bar.
- Next lever must be **new signal** (fresh residual review / recipe / scheme-targeted gold) — not another mem/warm clone.
- Keep launch default **`HYPERLEX_CUDA_MEM_FRACTION=0.3`**. Co-tenant → `0.03`.
- 9 abstain stay out. `name_gate` remains false. No Hub. No invent beyond labeled set.

## Policy

`name_gate=false`. Labeler authorized. Climb KEEP ≠ BEST. Full 40-epoch runs. One documented lever per climb. Fair-eval when val changes. No invent beyond labeled set.

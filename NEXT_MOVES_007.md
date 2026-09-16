# Spec 007 — morph42 REJECT_VS_BEST @ mem 0.3; BEST stays morph40

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST held:** **morph40** — `unbind_exact≈0.7368` (ep9) on fair val **n=228**. morph36 artifacts preserved. Climb KEEP famcls52 ≠ BEST.

## Status

morph40 BEST confirmed on spark. Civilian residual dump after morph40: **60** (PSM **28**).  
Residual review: **20** authorized structure / **8** abstain / **0** train promote → **NO_NEW_GOLD_THIS_CLIMB**.  
**morph41** warm morph40 @ mem **0.015** — **REJECT_VS_BEST** (best **0.7149** ep3 < fair **0.7368**). E2 PASS. ~85 min.  
**morph42** warm morph40 @ mem **0.3** — **REJECT_VS_BEST** (best **0.7149** ep3 < fair **0.7368**). E2 PASS. Container `hlx-train-morph42-1789542688` exited 0 (~**87 min**). Score matched morph41; **no wall speedup** from 0.3 on this recipe.

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
| morph41 warm morph40 @ 0.015 | **HIT** → **REJECT_VS_BEST** |
| morph42 warm morph40 @ **0.3** | **HIT** → **REJECT_VS_BEST** (same peak 0.7149; ~87 min) |
| Ladder `unbind_exact` ≥ **0.55** (comparable new val n=228) | **HIT** (0.7368) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| morph36 fair morph40 | 228 | 0.7325 | after 135 force-train |
| **morph40 BEST ep9** | **228** | **0.7368** | **PIN / held** |
| morph40 final ep39 | 228 | 0.6930 | SAVE_BEST kept ep9 |
| morph41 best ep3 @ 0.015 | 228 | **0.7149** | REJECT vs fair 0.7368 |
| morph42 best ep3 @ **0.3** | 228 | **0.7149** | REJECT vs fair 0.7368 |
| morph42 final ep39 | 228 | 0.6711 | SAVE_BEST kept ep3 |

## Pins

| pin | path | note |
|-----|------|------|
| **BEST** | morph40 | `...-seed-morph40` |
| morph36 | `...-seed-morph36` | preserved prior BEST |
| morph41 | `...-seed-morph41` | REJECT; weights kept |
| morph42 | `...-seed-morph42` | REJECT; weights kept |
| **residual review** | `receipts/morph40-residual-review-20260916/` | 20 auth / 0 promote |
| **morph41 reject** | `receipts/20260916-morph41-40ep-reject-vs-best.md` | |
| **morph42 reject** | `receipts/20260916-morph42-40ep-reject-vs-best.md` | mem 0.3; ~87 min |

## Next

- **Do not** schedule another warm-clone-of-morph40 climb (morph41/42 already REJECT at the same peak **0.7149**). Mem **0.3** is **not** the bottleneck (no wall speedup vs 0.015).
- Next lever = **residuals / gold / recipe**, not another warm clone: thin slice of the 20 held morph40 PSM auth rows; head-slot / curriculum / hard_atoms; or operator-directed gold. Fair-eval if val changes. **BEST stays morph40.**
- Keep launch default **`HYPERLEX_CUDA_MEM_FRACTION=0.3`** for headroom; do **not** expect shorter wall on ModernBERT last-N batch8 (still ~1.2 GiB resident). Co-tenant → `0.03`.
- 10 prior abstain + 1 documentary hold stay out. `name_gate` remains false. No Hub. No invent beyond labeled set.

## Policy

`name_gate=false`. Labeler authorized. Climb KEEP ≠ BEST. Full 40-epoch runs. One documented lever per climb. Fair-eval when val changes. No invent beyond labeled set.

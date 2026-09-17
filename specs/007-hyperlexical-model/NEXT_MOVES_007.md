# Spec 007 — morph47 curriculum POS=3 IN FLIGHT; BEST=morph40 held

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST held:** **morph40** — fair n=228 `unbind_exact≈0.7368` (ep9). morph36 preserved.

## Status

Warm-only morph41/42 REJECT. Residual-gold morph43/44 REJECT; high-conf gold **exhausted**.  
morph45 HEAD_SLOT=3 REJECT (0.7237 < 0.7368).  
morph46 HARD=6 REJECT (0.7149 < 0.7368).  
**morph47:** LEGAL — `CURRICULUM_POS_EPOCHS=3` (was 1) on morph40 surface; HEAD_SLOT=2 / HARD=4 held; warm morph40 + SAVE_BEST; mem 0.3; **IN FLIGHT**.

## Fair surface

morph40 force 135 / hard 180 → val **n=228** (no recompute). Gate **> 0.7368** to promote.

## Marks status (2026-09-17)

| mark | status |
|------|--------|
| morph40 PIN BEST | **HIT** (held) |
| morph41 / morph42 warm-only | **REJECT_VS_BEST** |
| morph43 / morph44 residual gold | **REJECT_VS_BEST** |
| Residual high-conf gold | **EXHAUSTED** |
| morph45 HEAD_SLOT=3 | **REJECT_VS_BEST** (0.7237 < 0.7368) |
| morph46 HARD=6 | **REJECT_VS_BEST** (0.7149 < 0.7368) |
| morph47 curriculum POS=3 | **IN FLIGHT** |
| Ladder ≥0.55 on n=228 | **HIT** (0.7368) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| **morph40 BEST** | 228 | **0.7368** | PIN / fair gate |
| morph45 best | 228 | 0.7237 | REJECT |
| morph46 best | 228 | 0.7149 | REJECT |
| morph47 | 228 | — | IN FLIGHT |

## Next

Gate morph47 vs fair 0.7368 on n=228. Promote only if best exceeds. Preserve morph40/morph36. `name_gate=false`. Remaining escalate levers if REJECT: LR / last-N.

## Policy

`name_gate=false`. Fair-eval when val changes (unchanged here). No invent beyond labeled set. No residual warm+force clones. No identical HEAD_SLOT=3.

# Spec 007 — morph45 REJECT_VS_BEST; BEST=morph40 held

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST held:** **morph40** — fair n=228 `unbind_exact≈0.7368` (ep9). morph36 preserved.

## Status

Warm-only morph41/42 REJECT. Residual-gold morph43/44 REJECT; high-conf gold **exhausted**.  
**morph45 attempt 1:** BLOCKED (invalid Spark `loop.py`).  
**morph45 attempt 2 (relaunch):** LEGAL execution on restored loop — **REJECT_VS_BEST** best **0.7237** (ep2) < fair **0.7368** (n=228). E2 PASS. BEST stays morph40.

## Fair surface

morph40 force 135 / hard 180 → val **n=228** (no recompute). Gate **> 0.7368** to promote — missed.

## Marks status (2026-09-17)

| mark | status |
|------|--------|
| morph40 PIN BEST | **HIT** (held) |
| morph41 / morph42 warm-only | **REJECT_VS_BEST** |
| morph43 / morph44 residual gold | **REJECT_VS_BEST** |
| Residual high-conf gold | **EXHAUSTED** |
| morph45 HEAD_SLOT=3 attempt1 | **BLOCKED** |
| morph45 HEAD_SLOT=3 relaunch | **REJECT_VS_BEST** (0.7237 < 0.7368) |
| Ladder ≥0.55 on n=228 | **HIT** (0.7368) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| **morph40 BEST** | 228 | **0.7368** | PIN / fair gate |
| morph45 best | 228 | **0.7237** | REJECT (ep2) |
| morph45 final | 228 | 0.7105 | ep39 |

## Next

HEAD_SLOT=3 on morph40 surface did not beat fair. Do not promote. Next lever ≠ another identical warm+HEAD_SLOT clone without a new justified delta. Preserve morph40/morph36. `name_gate=false`.

## Policy

`name_gate=false`. Fair-eval when val changes (unchanged here). No invent beyond labeled set.

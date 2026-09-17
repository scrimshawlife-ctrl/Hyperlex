# Spec 007 — morph49 PAUSED (CF tunnel); BEST=morph48 (0.7412)

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST:** **morph48** — fair n=228 `unbind_exact≈0.7412` (ep19). morph40 + morph36 preserved.

## Status

Warm-only morph41/42 REJECT. Residual-gold morph43/44 REJECT; high-conf gold **exhausted**.  
morph45 HEAD_SLOT=3 REJECT (0.7237 < 0.7368).  
morph46 HARD=6 REJECT (0.7149 < 0.7368).  
morph47 curriculum POS=3 REJECT (0.7149 < 0.7368).  
**morph48:** LEGAL — `HYPERLEX_LAST_TRAINABLE=6` → **PROMOTE_BEST** (0.7412 > 0.7368). E2 PASS.

**morph49 intent:** LEGAL — `HYPERLEX_LAST_TRAINABLE=7` (was 6), warm morph48, morph40 gold, SAVE_BEST, mem 0.3, 40ep. Fair gate **> 0.7412280701754386** on n=228.  
**PAUSED:** waiting on Cloudflare Tunnel recovery. Confirmed front-door failure (websocket bad handshake / HTTP 530 on ssh + qwen). Not keys/config. Receipt: `receipts/20260917-spark-tunnel-down.md` (also `receipts/20260917-morph49-ssh-blocked.md`). **No local fake-train.**

## Fair surface (morph49 gate)

morph40 force 135 / hard 180 → val **n=228**. Fair = morph48 BEST **0.7412280701754386** (recompute if val changes).

## Marks status (2026-09-17)

| mark | status |
|------|--------|
| morph40 prior BEST | **superseded** (preserved) |
| morph41 / morph42 warm-only | **REJECT_VS_BEST** |
| morph43 / morph44 residual gold | **REJECT_VS_BEST** |
| Residual high-conf gold | **EXHAUSTED** |
| morph45 HEAD_SLOT=3 | **REJECT_VS_BEST** |
| morph46 HARD=6 | **REJECT_VS_BEST** |
| morph47 curriculum POS=3 | **REJECT_VS_BEST** |
| morph48 LAST=6 | **PROMOTE_BEST / KEEP** (0.7412) |
| morph49 LAST=7 | **PAUSED** (CF tunnel; intent LEGAL; not launched) |
| Ladder ≥0.55 on n=228 | **HIT** (0.7412) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| **morph48 BEST** | 228 | **0.7412** | PIN (ep19) |
| morph40 prior | 228 | 0.7368 | preserved |
| morph49 | — | — | paused pre-launch |

## Next

1. **Operator:** restore CF tunnel until `ssh spark` → `spark-bf46`; confirm BEST→morph48 + restored loop.py.
2. Launch morph49 LAST=7; promote iff best > fair morph48.
3. On REJECT: morph50 with new delta (LAST=8 or LAST=6 + mild LR) — do not repeat exhausted knobs.

## Policy

`name_gate=false`. Single BEST pin → morph48. No Hub. Do not invent gold. Do not local fake-train while tunnel is down.
